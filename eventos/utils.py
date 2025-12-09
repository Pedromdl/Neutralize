# utils.py
from dateutil.rrule import rrule, rrulestr, DAILY, WEEKLY, MONTHLY
from dateutil.rrule import MO, TU, WE, TH, FR, SA, SU
from datetime import datetime, date, time, timedelta

WEEKDAY_MAP = {
    0: MO, 1: TU, 2: WE, 3: TH, 4: FR, 5: SA, 6: SU
}

def generate_rrule_from_simple(frequencia, start_date, repeticoes=None, byweekday=None, interval=1, until=None):
    """
    Gera um RRULE string baseado em seu modelo simples.
    - frequencia: "diario", "semanal", "mensal"
    - start_date: date object (usado como DTSTART)
    - repeticoes: número total de ocorrências (COUNT)
    - byweekday: lista de ints (0=segunda ... 6=domingo) para WEEKLY
    - interval: intervalo (padrão 1)
    - until: date de término (opcional)
    """
    parts = []
    if frequencia == "diario":
        parts.append("FREQ=DAILY")
    elif frequencia == "semanal":
        parts.append("FREQ=WEEKLY")
        if byweekday:
            # BYDAY=MO,WE,FR
            days = []
            for wd in byweekday:
                days.append(["MO","TU","WE","TH","FR","SA","SU"][wd])
            parts.append("BYDAY=" + ",".join(days))
    elif frequencia == "mensal":
        parts.append("FREQ=MONTHLY")
    else:
        return None

    if interval and int(interval) > 1:
        parts.append(f"INTERVAL={int(interval)}")

    if repeticoes:
        parts.append(f"COUNT={int(repeticoes)}")
    elif until:
        # until deve ser em UTC format YYYYMMDDT000000Z — aqui simplificamos para YYYYMMDD
        parts.append(f"UNTIL={until.strftime('%Y%m%d')}")

    return ";".join(parts)


def expand_rrule(rrule_str, dtstart_date, start, end):
    """
    Expande a rrule string entre start e end (date objects).
    Retorna lista de date objects (somente datas).
    dtstart_date: date -> usado como DTSTART
    """
    if not rrule_str:
        return []

    # construir string com DTSTART para rrulestr
    dtstart = datetime.combine(dtstart_date, time(0,0))
    # rrulestr entende DTSTART se receber string com DTSTART ou argumento dtstart
    rule = rrulestr(rrule_str, dtstart=dtstart)
    # rrule returns datetimes
    occurrences = list(rule.between(
        datetime.combine(start, time.min),
        datetime.combine(end, time.max),
        inc=True
    ))
    return [occ.date() for occ in occurrences]
