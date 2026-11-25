
import streamlit as st
import pandas as pd
from itertools import combinations

st.title("Stint Data")


# -------------------------
# Initialise session state
# -------------------------

if "stints" not in st.session_state:
    st.session_state.stints = []

if "next_stint_id" not in st.session_state:
    st.session_state.next_stint_id = 1

if "entry_version" not in st.session_state:
    st.session_state.entry_version = 0


# -------------------------
# Main layout
# -------------------------

left_col, right_col = st.columns([1.5, 1])


# -------------------------
# Left: New stint inputs
# -------------------------

with left_col:

    st.header("New Stint")

    col1, col2 = st.columns(2)

    with col1:
        stint_laps = st.number_input(
            "Number of laps in stint",
            min_value=1,
            value=10,
            step=1,
            key="stint_laps_input"
        )

    with col2:
        starting_fuel = st.number_input(
            "Starting fuel (laps)",
            min_value=0.0,
            value=20.0,
            step=0.5,
            key="starting_fuel_input"
        )

    st.subheader("Lap Times")

    version = st.session_state.entry_version

    # -------------------------
    # Paste lap times
    # -------------------------

    pasted_times = st.text_area(
        "Paste lap times (one per line)",
        height=150,
        key=f"pasted_times_{version}"
    )

    if st.button(
        "Load Lap Times",
        key=f"load_lap_times_{version}",
        use_container_width=True
    ):

        try:
            parsed_times = [
                float(line.strip())
                for line in pasted_times.splitlines()
                if line.strip()
            ]

            if len(parsed_times) != int(stint_laps):

                st.error(
                    f"You pasted {len(parsed_times)} lap times, "
                    f"but the stint is set to {int(stint_laps)} laps."
                )

            elif any(time < 0 for time in parsed_times):

                st.error("Lap times cannot be negative.")

            else:

                for lap, lap_time in enumerate(parsed_times):

                    st.session_state[
                        f"lap_time_{version}_{lap}"
                    ] = lap_time

                st.success(
                    f"Successfully loaded {len(parsed_times)} lap times."
                )

        except ValueError:

            st.error(
                "Invalid lap time. Please enter numbers only, "
                "with one lap time per line."
            )

    # -------------------------
    # Individual lap inputs
    # -------------------------

    lap_times = []
    ignored_laps = []

    for lap in range(int(stint_laps)):

        col1, col2 = st.columns([2, 1])

        with col1:

            lap_time = st.number_input(
                f"Lap {lap + 1}",
                min_value=0.0,
                value=100.0,
                step=0.001,
                format="%.3f",
                key=f"lap_time_{version}_{lap}"
            )

        with col2:

            ignore = st.checkbox(
                "Ignore",
                key=f"ignore_lap_{version}_{lap}"
            )

        lap_times.append(lap_time)
        ignored_laps.append(ignore)

    # -------------------------
    # Add stint
    # -------------------------

    if st.button(
        "Add Stint",
        type="primary",
        use_container_width=True,
        key=f"add_stint_{version}"
    ):

        stint_id = st.session_state.next_stint_id

        stint = {
            "ID": stint_id,
            "Stint": stint_id,
            "Laps": int(stint_laps),
            "Starting Fuel (laps)": starting_fuel,
            "Lap Times": lap_times,
            "Ignored Laps": ignored_laps
        }

        st.session_state.stints.append(stint)

        st.session_state.next_stint_id += 1
        st.session_state.entry_version += 1

        st.rerun()


# -------------------------
# Calculate fuel, tyre and base lap
# -------------------------

fuel_loss = None
tyre_loss = None
base_lap = None

fuel_estimates = []

if len(st.session_state.stints) >= 2:

    # Compare every possible pair of stints

    for stint1, stint2 in combinations(st.session_state.stints, 2):

        fuel_diff = (
            stint1["Starting Fuel (laps)"]
            - stint2["Starting Fuel (laps)"]
        )

        # Skip pairs with identical starting fuel

        if abs(fuel_diff) < 0.001:
            continue

        common_laps = min(
            stint1["Laps"],
            stint2["Laps"]
        )

        lap_differences = []

        for i in range(common_laps):

            if stint1["Ignored Laps"][i]:
                continue

            if stint2["Ignored Laps"][i]:
                continue

            lap_differences.append(
                stint1["Lap Times"][i]
                - stint2["Lap Times"][i]
            )

        if lap_differences:

            pair_fuel_loss = (
                sum(lap_differences)
                / len(lap_differences)
                / fuel_diff
            )

            fuel_estimates.append(pair_fuel_loss)

    # Average all usable fuel estimates

    if fuel_estimates:

        fuel_loss = (
            sum(fuel_estimates)
            / len(fuel_estimates)
        )

        # -------------------------
        # Calculate tyre degradation
        # -------------------------

        total_tyre_difference = 0
        total_transitions = 0

        for stint in st.session_state.stints:

            for i in range(stint["Laps"] - 1):

                if stint["Ignored Laps"][i]:
                    continue

                if stint["Ignored Laps"][i + 1]:
                    continue

                total_tyre_difference += (
                    stint["Lap Times"][i + 1]
                    - stint["Lap Times"][i]
                    + fuel_loss
                )

                total_transitions += 1

        if total_transitions > 0:

            tyre_loss = (
                total_tyre_difference
                / total_transitions
            )

        # -------------------------
        # Calculate base lap time
        # -------------------------

        if tyre_loss is not None:

            base_lap_estimates = []

            for stint in st.session_state.stints:

                starting_fuel = stint["Starting Fuel (laps)"]

                for i, lap_time in enumerate(stint["Lap Times"]):

                    if stint["Ignored Laps"][i]:
                        continue

                    fuel_amount = starting_fuel - i
                    tyre_age = i

                    estimated_base = (
                        lap_time
                        - (fuel_amount * fuel_loss)
                        - (tyre_age * tyre_loss)
                    )

                    base_lap_estimates.append(estimated_base)

            if base_lap_estimates:

                base_lap = (
                    sum(base_lap_estimates)
                    / len(base_lap_estimates)
                )


# -------------------------
# Right: Estimated losses
# -------------------------

with right_col:

    st.header("Estimated Losses")

    st.caption("Calculated from all saved stints.")

    if len(st.session_state.stints) < 2:

        st.info(
            "More stints required to calculate fuel and tyre loss."
        )

    elif fuel_loss is None:

        st.info(
            "More data required. At least two stints with different "
            "starting fuel loads and matching valid laps are needed."
        )

    else:

        st.metric(
            "Base Lap",
            f"{base_lap:.3f} seconds"
            if base_lap is not None
            else "N/A"
        )

        st.metric(
            "Fuel Loss",
            f"{fuel_loss:.4f} s/lap/lap"
        )

        if tyre_loss is not None:

            st.metric(
                "Tyre Loss",
                f"{tyre_loss:.4f} s/lap"
            )

        else:

            st.info(
                "More consecutive valid laps required to calculate tyre loss."
            )

        st.caption(
            f"Based on {len(fuel_estimates)} usable stint comparisons."
        )


# -------------------------
# Recorded stints
# -------------------------

st.divider()
st.header("Recorded Stints")

if st.session_state.stints:

    for stint in st.session_state.stints:

        with st.expander(
            f"Stint {stint['Stint']} - {stint['Laps']} laps"
        ):

            st.write(
                f"Starting fuel: {stint['Starting Fuel (laps)']} laps"
            )

            for lap_index, lap_time in enumerate(stint["Lap Times"]):

                if stint["Ignored Laps"][lap_index]:

                    st.write(
                        f"Lap {lap_index + 1}: "
                        f"{lap_time:.3f} seconds — Ignored"
                    )

                else:

                    st.write(
                        f"Lap {lap_index + 1}: "
                        f"{lap_time:.3f} seconds"
                    )

            valid_times = [
                time
                for time, ignored in zip(
                    stint["Lap Times"],
                    stint["Ignored Laps"]
                )
                if not ignored
            ]

            if valid_times:

                average = sum(valid_times) / len(valid_times)

                st.write(
                    f"Average lap time: {average:.3f} seconds"
                )

            else:

                st.write(
                    "Average lap time: N/A (all laps ignored)"
                )

            st.write(
                f"Ignored laps: "
                f"{sum(stint['Ignored Laps'])} / {stint['Laps']}"
            )

            if st.button(
                "Delete Stint",
                key=f"delete_stint_{stint['ID']}"
            ):

                st.session_state.stints = [
                    s for s in st.session_state.stints
                    if s["ID"] != stint["ID"]
                ]

                st.rerun()

    # -------------------------
    # Stint summary
    # -------------------------

    summary_data = []

    for stint in st.session_state.stints:

        valid_times = [
            time
            for time, ignored in zip(
                stint["Lap Times"],
                stint["Ignored Laps"]
            )
            if not ignored
        ]

        average = (
            sum(valid_times) / len(valid_times)
            if valid_times else None
        )

        summary_data.append({

            "Stint": stint["Stint"],
            "Laps": stint["Laps"],
            "Starting Fuel (laps)": stint["Starting Fuel (laps)"],
            "Ignored Laps": sum(stint["Ignored Laps"]),
            "Valid Laps": len(valid_times),

            "Average Lap Time": (
                f"{average:.3f}"
                if average is not None
                else "N/A"
            )
        })

    st.subheader("Stint Summary")

    st.dataframe(
        pd.DataFrame(summary_data),
        hide_index=True,
        use_container_width=True
    )

    if st.button(
        "Clear All Stints",
        key="clear_all_stints"
    ):

        st.session_state.stints = []
        st.rerun()

else:

    st.info("No stints have been recorded yet.")
