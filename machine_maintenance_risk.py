import sys


def build_output(
    reference_day,
    machine_count,
    profile_count,
    reading_count,
    maintenance_count,
    fault_count,
    machine_records,
    profile_records,
    reading_records,
    maintenance_records,
    fault_records,
):
    # machineId -> (machineName, machineType, inputIndex)
    machines = {}
    machine_order = []
    for idx, rec in enumerate(machine_records):
        machine_id, machine_name, machine_type = rec[0], rec[1], rec[2]
        machines[machine_id] = (machine_name, machine_type, idx)
        machine_order.append(machine_id)

    # machineType -> (maxTemperature, maxVibration)
    profiles = {}
    for rec in profile_records:
        machine_type = rec[0]
        max_temperature = int(rec[1])
        max_vibration = int(rec[2])
        profiles[machine_type] = (max_temperature, max_vibration)

    # Per-machine aggregates from valid sensor readings
    valid_reading_count = {mid: 0 for mid in machines}
    total_temperature = {mid: 0 for mid in machines}
    total_vibration = {mid: 0 for mid in machines}
    temperature_breach_count = {mid: 0 for mid in machines}
    vibration_breach_count = {mid: 0 for mid in machines}

    # Per machine-type totals for type average temperature
    type_temp_total = {}
    type_reading_count = {}

    for rec in reading_records:
        machine_id = rec[1]
        if machine_id not in machines:
            continue
        reading_day = int(rec[2])
        temperature = int(rec[3])
        vibration = int(rec[4])
        if reading_day < 1 or reading_day > reference_day:
            continue
        if temperature < 0 or vibration < 0:
            continue

        machine_type = machines[machine_id][1]
        max_temperature, max_vibration = profiles[machine_type]

        valid_reading_count[machine_id] += 1
        total_temperature[machine_id] += temperature
        total_vibration[machine_id] += vibration
        if temperature > max_temperature:
            temperature_breach_count[machine_id] += 1
        if vibration > max_vibration:
            vibration_breach_count[machine_id] += 1

        type_temp_total[machine_type] = type_temp_total.get(machine_type, 0) + temperature
        type_reading_count[machine_type] = type_reading_count.get(machine_type, 0) + 1

    machine_type_avg_temperature = {}
    for machine_type, count in type_reading_count.items():
        if count == 0:
            machine_type_avg_temperature[machine_type] = 0
        else:
            machine_type_avg_temperature[machine_type] = type_temp_total[machine_type] // count

    # Ensure every machine type seen in machines has an entry
    for mid in machines:
        mtype = machines[mid][1]
        if mtype not in machine_type_avg_temperature:
            machine_type_avg_temperature[mtype] = 0

    # Latest valid maintenance day per machine
    latest_maintenance_day = {}
    for rec in maintenance_records:
        machine_id = rec[1]
        if machine_id not in machines:
            continue
        maintenance_day = int(rec[2])
        maintenance_type = rec[3]
        if maintenance_type not in ("PREVENTIVE", "CORRECTIVE"):
            continue
        if maintenance_day < 1 or maintenance_day > reference_day:
            continue
        if machine_id not in latest_maintenance_day or maintenance_day > latest_maintenance_day[machine_id]:
            latest_maintenance_day[machine_id] = maintenance_day

    # High severity fault counts
    high_severity_fault_count = {mid: 0 for mid in machines}
    for rec in fault_records:
        machine_id = rec[1]
        if machine_id not in machines:
            continue
        event_day = int(rec[2])
        severity = rec[3]
        if severity not in ("LOW", "MEDIUM", "HIGH"):
            continue
        if event_day < 1 or event_day > reference_day:
            continue
        if severity == "HIGH":
            high_severity_fault_count[machine_id] += 1

    results = []
    for machine_id in machine_order:
        machine_name, machine_type, input_index = machines[machine_id]
        max_temperature, max_vibration = profiles[machine_type]

        vrc = valid_reading_count[machine_id]
        if vrc == 0:
            average_temperature = 0
            average_vibration = 0
        else:
            average_temperature = total_temperature[machine_id] // vrc
            average_vibration = total_vibration[machine_id] // vrc

        has_maintenance = machine_id in latest_maintenance_day
        if has_maintenance:
            days_since_maintenance = reference_day - latest_maintenance_day[machine_id]
        else:
            days_since_maintenance = reference_day + 1

        type_avg_temp = machine_type_avg_temperature[machine_type]
        above_temperature_baseline = vrc > 0 and average_temperature > type_avg_temp

        risk_score = 0
        if days_since_maintenance >= 90:
            risk_score += 4
        if not has_maintenance:
            risk_score += 3
        if temperature_breach_count[machine_id] >= 2:
            risk_score += 3
        if vibration_breach_count[machine_id] >= 2:
            risk_score += 3
        if high_severity_fault_count[machine_id] >= 1:
            risk_score += 3
        if above_temperature_baseline:
            risk_score += 2
        if vrc > 0 and average_vibration > max_vibration:
            risk_score += 2

        if risk_score >= 10:
            risk_level = "HIGH"
        elif risk_score >= 6:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        if risk_level in ("HIGH", "MEDIUM"):
            results.append(
                (
                    0 if risk_level == "HIGH" else 1,
                    -risk_score,
                    -days_since_maintenance,
                    input_index,
                    f"{machine_name}-{risk_level}-{risk_score}-{days_since_maintenance}",
                )
            )

    if not results:
        return "NA"

    results.sort()
    return "#".join(item[4] for item in results)


def main():
    input_data = sys.stdin.buffer.readline

    reference_day_line = input_data().decode().strip()
    if not reference_day_line:
        return

    reference_day = int(reference_day_line)

    machine_count = int(input_data())
    profile_count = int(input_data())
    reading_count = int(input_data())
    maintenance_count = int(input_data())
    fault_count = int(input_data())

    machine_records = [
        input_data().decode().split()
        for _ in range(machine_count)
    ]

    profile_records = [
        input_data().decode().split()
        for _ in range(profile_count)
    ]

    reading_records = [
        input_data().decode().split()
        for _ in range(reading_count)
    ]

    maintenance_records = [
        input_data().decode().split()
        for _ in range(maintenance_count)
    ]

    fault_records = [
        input_data().decode().split()
        for _ in range(fault_count)
    ]

    print(
        build_output(
            reference_day,
            machine_count,
            profile_count,
            reading_count,
            maintenance_count,
            fault_count,
            machine_records,
            profile_records,
            reading_records,
            maintenance_records,
            fault_records,
        )
    )


if __name__ == "__main__":
    main()
