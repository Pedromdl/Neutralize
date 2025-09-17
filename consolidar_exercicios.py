from orientacoes.models import ExercicioExecutado

def deduplicar_seriess():
    todos = ExercicioExecutado.objects.all()
    for ex in todos:
        series = ex.seriess  # supondo que seja um campo JSON
        if series:
            # remover duplicados
            seen = set()
            novas_series = []
            for s in series:
                # transforma em tupla para permitir comparação em set
                t = (s.get("numero"), s.get("repeticoes"), s.get("carga"))
                if t not in seen:
                    seen.add(t)
                    novas_series.append(s)
            # só atualiza se realmente houve mudanças
            if len(novas_series) != len(series):
                ex.seriess = novas_series
                ex.save()
                print(f"{ex.id} atualizado, {len(series)} -> {len(novas_series)} séries")

deduplicar_seriess()
