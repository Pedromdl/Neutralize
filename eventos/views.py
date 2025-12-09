# views.py
from django.shortcuts import render
from httpcore import request
from .models import EventoAgenda, EventoExcecao
from .serializers import EventoAgendaSerializer
from django_filters.rest_framework import DjangoFilterBackend
from datetime import timedelta, datetime, time
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
import calendar
from api.mixins import OrganizacaoFilterMixin
from .utils import expand_rrule, generate_rrule_from_simple
from dateutil.rrule import rrulestr

class EventoAgendaViewSet(OrganizacaoFilterMixin, viewsets.ModelViewSet):
    lookup_field = "pk"
    lookup_value_regex = "[^/]+"
    queryset = EventoAgenda.objects.all()
    serializer_class = EventoAgendaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['paciente']
    organizacao_field = "organizacao"

    def get_serializer_class(self):
        from .serializers import EventoAgendaResumoSerializer
        if self.action == 'list':
            return EventoAgendaResumoSerializer
        return EventoAgendaSerializer

    def get_queryset(self):
        return super().get_queryset().select_related('paciente')

    def expandir_eventos_rrule(self, start, end):
        """
        Expande todos os eventos com RRULE entre start e end,
        aplicando EXDATES e exceções. Retorna lista de dicts.
        """
        # 🔹 Converte strings do query param para datetime.datetime
        start_dt = datetime.fromisoformat(start + "T00:00:00")
        end_dt = datetime.fromisoformat(end + "T23:59:59")

        resultados = []

        # buscar só eventos com rrule (pais)
        eventos_rrule = self.get_queryset().filter(rrule__isnull=False)

        for ev in eventos_rrule:
            # cria a regra rrule
            try:
                from dateutil.rrule import rrulestr
                regra = rrulestr(ev.rrule, dtstart=datetime.combine(ev.data, ev.hora_inicio or time.min))
            except Exception:
                continue

            # gera instâncias entre start e end
            instancias = regra.between(start_dt, end_dt, inc=True)

            # aplica EXDATES
            if ev.exdates:
                instancias = [d for d in instancias if d.date() not in ev.exdates]

            # map de exceções por recurrence_id
            excecoes = {}
            try:
                for ex in getattr(ev, "excecoes").all():
                    excecoes[ex.recurrence_id] = ex
            except Exception:
                excecoes = {}

            for dt_ocorr in instancias:
                data_ocorr = dt_ocorr.date()
                # se houver exceção, usa dados sobrescritos
                if data_ocorr in excecoes:
                    ex = excecoes[data_ocorr]
                    resultados.append({
                        "id": f"virt-{ev.id}-{data_ocorr.isoformat()}",
                        "paciente": ex.evento_pai.paciente.id if ex.evento_pai and ex.evento_pai.paciente else None,
                        "paciente_nome": ev.paciente.nome if ev.paciente else None,  # ✅ aqui
                        "tipo": ex.tipo or ev.tipo,
                        "status": ex.status or ev.status,
                        "data": str(ex.data),
                        "hora_inicio": str(ex.hora_inicio),
                        "hora_fim": str(ex.hora_fim) if ex.hora_fim else None,
                        "responsavel": ex.responsavel or ev.responsavel,
                        "rrule": ev.rrule,
                        "evento_pai": ev.id,
                        "is_recorrencia": True,
                    })
                else:
                    resultados.append({
                        "id": f"virt-{ev.id}-{data_ocorr.isoformat()}",
                        "paciente": ev.paciente.id if ev.paciente else None,
                        "paciente_nome": ev.paciente.nome if ev.paciente else None,
                        "tipo": ev.tipo,
                        "status": ev.status,
                        "data": str(data_ocorr),
                        "hora_inicio": str(ev.hora_inicio),
                        "hora_fim": str(ev.hora_fim) if ev.hora_fim else None,
                        "responsavel": ev.responsavel,
                        "rrule": ev.rrule,
                        "evento_pai": ev.id,
                        "is_recorrencia": True,
                    })

        return resultados


    def list(self, request, *args, **kwargs):
        start = request.query_params.get("start")
        end = request.query_params.get("end")

        if not start or not end:
            return Response([], status=200)

        # parse das datas
        try:
            start_date = datetime.fromisoformat(start).date()
            end_date = datetime.fromisoformat(end).date()
        except ValueError:
            return Response({"erro": "start/end inválidos. Use YYYY-MM-DD."}, status=400)

        # ==========================
        # 1) Buscar eventos "reais" (sem rrule) no range
        # ==========================
        # inclui filhos físicos legados (evento_pai is not null) e eventos únicos (rrule is null)
        qs = self.get_queryset().filter(
            rrule__isnull=True,
            data__gte=start_date,
            data__lte=end_date
        )

        serialized = EventoAgendaSerializer(qs, many=True).data

        eventos_normais = []
        for ev in serialized:
            eventos_normais.append({
                **ev,
                "data": str(ev["data"]),
                "hora_inicio": str(ev["hora_inicio"]),
                "hora_fim": str(ev["hora_fim"]) if ev["hora_fim"] else None,
            })

        # ==========================
        # 2) Expandir eventos com RRULE (pais)
        # ==========================
        eventos_expand = self.expandir_eventos_rrule(start, end)

        # ==========================
        # 3) Combinar e normalizar
        # ==========================
        combined = eventos_normais + eventos_expand

        def normalizar(e):
            return {
                **e,
                "data": str(e["data"]),
                "hora_inicio": str(e["hora_inicio"]) if e.get("hora_inicio") is not None else None,
                "hora_fim": str(e["hora_fim"]) if e.get("hora_fim") is not None else None,
            }

        combined = [normalizar(e) for e in combined]

        # ==========================
        # 4) Ordenação segura por strings YYYY-MM-DD e HH:MM:SS
        # ==========================
        combined_sorted = sorted(combined, key=lambda x: (x["data"], x.get("hora_inicio") or "00:00:00"))

        return Response(combined_sorted, status=200)
    
    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        repetir = data.get("repetir") in [True, "true", "True", "1", 1]
        frequencia = data.get("frequencia")
        repeticoes = data.get("repeticoes")
        byweekday = data.get("dias_semana", None)

        organizacao = request.user.organizacao

        # 1) Criar evento pai
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        evento_principal = serializer.save(organizacao=organizacao)

        # 🔥 IMPORTANTE: recarregar para popular paciente_nome
        evento_principal.refresh_from_db()

        # 2) Gerar RRULE se for recorrente
        if repetir and frequencia and frequencia != "nenhuma":

            if isinstance(byweekday, str):
                try:
                    import json
                    byweekday = json.loads(byweekday)
                except Exception:
                    byweekday = None

            rrule_str = generate_rrule_from_simple(
                frequencia=frequencia,
                start_date=evento_principal.data,
                repeticoes=repeticoes,
                byweekday=byweekday,
                interval=data.get("intervalo", 1),
                until=None
            )

            evento_principal.rrule = rrule_str
            evento_principal.repeticoes = int(repeticoes) if repeticoes else None
            evento_principal.repetir = True
            evento_principal.save()

            # recarrega novamente após modificar os campos
            evento_principal.refresh_from_db()

        return Response(self.get_serializer(evento_principal).data, status=201)



        # ---------------------------------------
        # 2) EVENTO REAL (não virtual)
        # ---------------------------------------
        evento = self.get_object()
        serializer = self.get_serializer(evento, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        if evento.rrule:  # evento pai recorrente
            if escopo == "unico":
                # criar EventoExcecao
                ex = EventoExcecao.objects.create(
                    evento_pai=evento,
                    recurrence_id=evento.data,
                    **serializer.validated_data
                )
                return Response(self.get_serializer(ex).data, status=200)
            elif escopo == "futuros":
                regra = rrulestr(evento.rrule, dtstart=evento.data)
                novo_until = evento.data - timedelta(days=1)
                evento.rrule = str(regra.replace(until=novo_until))
                serializer.save()
                return Response(self.get_serializer(evento).data, status=200)
            elif escopo == "todos":
                serializer.save()
                return Response(self.get_serializer(evento).data, status=200)
            else:
                return Response({"detail": "Escopo inválido."}, status=400)

        # evento simples
        serializer.save()
        return Response(self.get_serializer(evento).data, status=200)
    
    def update(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        escopo = request.data.get("escopo_edicao", "unico")

        # ---------------------------------------
        # 1) EVENTO VIRTUAL: virt-<id>-<YYYY-MM-DD>
        # ---------------------------------------
        if isinstance(pk, str) and pk.startswith("virt-"):
            try:
                _, evento_id, data_str = pk.split("-", maxsplit=2)
                recurrence_date = datetime.fromisoformat(data_str).date()
            except Exception:
                return Response({"detail": "Formato de ID virtual inválido."}, status=400)

            try:
                evento_pai = EventoAgenda.objects.get(id=evento_id)
            except EventoAgenda.DoesNotExist:
                return Response({"detail": "Evento pai não encontrado."}, status=404)

            # ──────────── UNICO ────────────
            if escopo == "unico":
                # Cria ou atualiza EventoExcecao
                defaults = {
                    "data": recurrence_date,
                    "hora_inicio": request.data.get("hora_inicio", evento_pai.hora_inicio),
                    "hora_fim": request.data.get("hora_fim", evento_pai.hora_fim),
                    "tipo": request.data.get("tipo", evento_pai.tipo),
                    "status": request.data.get("status", evento_pai.status),
                    "responsavel": request.data.get("responsavel", evento_pai.responsavel),
                    "evento_pai": evento_pai,
                    "recurrence_id": recurrence_date,
                }
                EventoExcecao.objects.update_or_create(
                    evento_pai=evento_pai,
                    recurrence_id=recurrence_date,
                    defaults=defaults
                )
                return Response({"detail": "Exceção criada/atualizada com sucesso."}, status=200)

            # ──────────── FUTUROS ────────────
            elif escopo == "futuros":
                from dateutil.rrule import rrulestr

                regra = rrulestr(evento_pai.rrule, dtstart=evento_pai.data)
                novo_until = recurrence_date - timedelta(days=1)
                evento_pai.rrule = str(regra.replace(until=novo_until))
                evento_pai.save()
                return Response({"detail": "RRULE atualizada para futuros eventos."}, status=200)

            # ──────────── TODOS ────────────
            elif escopo == "todos":
                evento_pai.delete()
                return Response({"detail": "Todos os eventos da série excluídos."}, status=204)

            else:
                return Response({"detail": "Escopo inválido."}, status=400)

        # ---------------------------------------
        # 2) EVENTO REAL (não virtual)
        # ---------------------------------------
        evento = self.get_object()

        # ──────────── SEM RRULE → UPDATE NORMAL ────────────
        if not evento.rrule:
            serializer = self.get_serializer(evento, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=200)

        # ──────────── EVENTO REAL COM RRULE ────────────
        if escopo == "todos":
            serializer = self.get_serializer(evento, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=200)

        elif escopo == "futuros":
            from dateutil.rrule import rrulestr

            regra = rrulestr(evento.rrule, dtstart=evento.data)
            novo_until = evento.data - timedelta(days=1)
            evento.rrule = str(regra.replace(until=novo_until))
            evento.save()
            return Response({"detail": "RRULE atualizada para futuros eventos."}, status=200)

        elif escopo == "unico":
            # Cria EventoExcecao para a data específica
            recurrence_date = evento.data
            defaults = {
                "data": request.data.get("data", evento.data),
                "hora_inicio": request.data.get("hora_inicio", evento.hora_inicio),
                "hora_fim": request.data.get("hora_fim", evento.hora_fim),
                "tipo": request.data.get("tipo", evento.tipo),
                "status": request.data.get("status", evento.status),
                "responsavel": request.data.get("responsavel", evento.responsavel),
                "evento_pai": evento,
                "recurrence_id": recurrence_date,
            }
            EventoExcecao.objects.update_or_create(
                evento_pai=evento,
                recurrence_id=recurrence_date,
                defaults=defaults
            )
            return Response({"detail": "Exceção criada/atualizada com sucesso."}, status=200)

        else:
            return Response({"detail": "Escopo inválido."}, status=400)


    
    def destroy(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        escopo = request.data.get("escopo_exclusao", "unico")

        # ---------------------------------------
        # 1) CASO SEJA EVENTO VIRTUAL: virt-<id>-<YYYY-MM-DD>
        # ---------------------------------------
        if isinstance(pk, str) and pk.startswith("virt-"):
            try:
                _, evento_id, data_str = pk.split("-", maxsplit=2)
                data_ocorr = datetime.fromisoformat(data_str).date()
            except Exception:
                return Response({"detail": "Formato de ID virtual inválido."}, status=400)

            try:
                evento_pai = EventoAgenda.objects.get(id=evento_id)
            except EventoAgenda.DoesNotExist:
                return Response({"detail": "Evento pai não encontrado."}, status=404)

            # ─────────────────────────────────────────────
            # UNICO → adicionar EXDATE apenas para essa data
            # ─────────────────────────────────────────────
            if escopo == "unico":
                exd = set(evento_pai.exdates or [])
                exd.add(data_ocorr)
                evento_pai.exdates = sorted(list(exd))
                evento_pai.save()
                return Response(status=204)

            # ─────────────────────────────────────────────
            # FUTUROS → ajustar RRULE para terminar no dia anterior
            # ─────────────────────────────────────────────
            if escopo == "futuros":
                from dateutil.rrule import rrulestr

                regra = rrulestr(evento_pai.rrule, dtstart=evento_pai.data)
                novo_until = data_ocorr - timedelta(days=1)

                rrule_str = str(regra.replace(until=novo_until))
                evento_pai.rrule = rrule_str
                evento_pai.save()
                return Response(status=204)

            # ─────────────────────────────────────────────
            # TODOS → apagar o evento pai (fim da série)
            # ─────────────────────────────────────────────
            if escopo == "todos":
                evento_pai.delete()
                return Response(status=204)

            return Response({"detail": "Escopo inválido."}, status=400)

        # ---------------------------------------
        # 2) EVENTO REAL (não virtual)
        # ---------------------------------------
        evento = self.get_object()

        # sem RRULE → apagar normal
        if not evento.rrule:
            return super().destroy(request, *args, **kwargs)

        # evento real mas com RRULE (pai)
        if escopo == "todos":
            evento.delete()
            return Response(status=204)

        if escopo == "futuros":
            from dateutil.rrule import rrulestr

            regra = rrulestr(evento.rrule, dtstart=evento.data)
            novo_until = evento.data - timedelta(days=1)

            evento.rrule = str(regra.replace(until=novo_until))
            evento.save()
            return Response(status=204)

        if escopo == "unico":
            exd = set(evento.exdates or [])
            exd.add(evento.data)
            evento.exdates = sorted(list(exd))
            evento.save()
            return Response(status=204)

        return Response({"detail": "Escopo inválido."}, status=400)
