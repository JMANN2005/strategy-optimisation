#       python -m streamlit run "strategy optimisation.py"  


import streamlit as st
import pandas as pd
import math

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Race Strategy Optimiser",
    layout="wide"
)

st.title("Race Strategy Optimiser")


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "custom_strategies" not in st.session_state:
    st.session_state.custom_strategies = []

if "next_custom_id" not in st.session_state:
    st.session_state.next_custom_id = 1

if "race_config" not in st.session_state:
    st.session_state.race_config = None

if "optimal_strategy" not in st.session_state:
    st.session_state.optimal_strategy = None




# --------------------------------------------------
# RACE CONFIGURATION
# --------------------------------------------------

st.header("Race Configuration")

with st.form("race_configuration"):

    col1, col2, col3 = st.columns(3)

    with col1:
        fuel_consumption_input = st.number_input(
            "Fuel consumption (L/lap)",
            min_value=0.1,
            value=None,
            step=0.1
        )

    with col2:
        race_laps_input = st.number_input(
            "Race distance (laps)",
            min_value=2,
            value=None,
            step=1
        )

    with col3:
        max_tank_input = st.number_input(
            "Maximum tank capacity (L)",
            min_value=1,
            value=None,
            step=1
        )

    st.subheader("Performance Parameters")

    col1, col2, col3 = st.columns(3)

    with col1:
        base_lap_input = st.number_input(
            "Base lap time (seconds)",
            min_value=1.0,
            value=None,
            step=0.1
        )

    with col2:
        fuel_penalty_input = st.number_input(
            "Fuel penalty (seconds/lap per lap of fuel)",
            min_value=0.0,
            value=None,
            step=0.001,
            format="%.3f"
        )

    with col3:
        tyre_degradation_input = st.number_input(
            "Tyre degradation (seconds/lap)",
            min_value=0.0,
            value=None,
            step=0.001,
            format="%.3f"
        )

    st.subheader("Pit Stop Parameters")

    col1, col2, col3 = st.columns(3)

    with col1:
        pit_lane_loss_input = st.number_input(
            "Pit lane loss (seconds)",
            min_value=0.0,
            value=None,
            step=0.5
        )

    with col2:
        refuel_time_input = st.number_input(
            "Refuelling time (seconds/litre)",
            min_value=0.0,
            value=None,
            step=0.1
        )

    with col3:
        tyre_change_time_input = st.number_input(
            "Tyre change time (seconds)",
            min_value=0.0,
            value=None,
            step=0.5
        )

    recalculate = st.form_submit_button(
        "Recalculate Strategy",
        type="primary",
        use_container_width=True
    )

if recalculate:

    inputs = [
        fuel_consumption_input,
        race_laps_input,
        max_tank_input,
        base_lap_input,
        fuel_penalty_input,
        tyre_degradation_input,
        pit_lane_loss_input,
        refuel_time_input,
        tyre_change_time_input
    ]

    if any(value is None for value in inputs):
        st.error("Please complete all configuration fields.")
        st.stop()

    if fuel_consumption_input > max_tank_input:
        st.error("Fuel consumption per lap cannot exceed tank capacity.")
        st.stop()

    st.session_state.race_config = {
        "fuel_consumption": fuel_consumption_input,
        "race_laps": int(race_laps_input),
        "max_tank": int(max_tank_input),
        "base_lap": base_lap_input,
        "fuel_penalty": fuel_penalty_input,
        "tyre_degradation": tyre_degradation_input,
        "pit_lane_loss": pit_lane_loss_input,
        "refuel_time": refuel_time_input,
        "tyre_change_time": tyre_change_time_input
    }

    st.session_state.custom_strategies = []
    st.session_state.next_custom_id = 1
    st.session_state.optimal_strategy = None




# --------------------------------------------------
# LOAD CONFIGURATION
# --------------------------------------------------

if st.session_state.race_config is None:
    st.info("Enter your race parameters above to calculate a strategy.")
    st.stop()

config = st.session_state.race_config

fuel_consumption = config["fuel_consumption"]
race_laps = config["race_laps"]
max_tank = config["max_tank"]
base_lap = config["base_lap"]
fuel_penalty = config["fuel_penalty"]
tyre_degradation = config["tyre_degradation"]
pit_lane_loss = config["pit_lane_loss"]
refuel_time = config["refuel_time"]
tyre_change_time = config["tyre_change_time"]


# --------------------------------------------------
# MODEL FUNCTIONS
# --------------------------------------------------

def calculate_lap_time(fuel, tyre_age):

    # Convert fuel in litres into laps of fuel.
    # The original fuel penalty is measured per lap of fuel.

    fuel_in_laps = fuel / fuel_consumption

    return (
        base_lap
        + fuel_in_laps * fuel_penalty
        + tyre_age * tyre_degradation
    )


def calculate_pit_time(fuel_added, change_tyres):

    fuel_time = fuel_added * refuel_time

    tyre_time = tyre_change_time if change_tyres else 0

    return pit_lane_loss + max(fuel_time, tyre_time)


# --------------------------------------------------
# STRATEGY SIMULATION
# --------------------------------------------------

def simulate_strategy(starting_fuel, pit_stops):

    fuel = float(starting_fuel)
    tyre_age = 0

    total_time = 0.0

    cumulative_times = [0.0]
    lap_times = []

    pit_stop_dict = {
        stop[0]: stop
        for stop in pit_stops
    }

    for lap in range(1, race_laps + 1):

        # Check that there is enough fuel to complete the lap

        if fuel < fuel_consumption - 0.000001:
            return None

        # Calculate lap time using fuel at the start of the lap

        lap_time = calculate_lap_time(fuel, tyre_age)

        total_time += lap_time
        lap_times.append(lap_time)

        fuel -= fuel_consumption
        fuel = round(fuel, 6)

        tyre_age += 1

        # Apply pit stop after completing the lap

        if lap in pit_stop_dict:

            _, fuel_added, change_tyres = pit_stop_dict[lap]

            if fuel + fuel_added > max_tank + 0.000001:
                return None

            fuel += fuel_added

            pit_time = calculate_pit_time(
                fuel_added,
                change_tyres
            )

            total_time += pit_time

            if change_tyres:
                tyre_age = 0

        cumulative_times.append(total_time)

    return {
        "total_time": total_time,
        "cumulative_times": cumulative_times,
        "lap_times": lap_times
    }


# --------------------------------------------------
# OPTIMAL STRATEGY - DYNAMIC PROGRAMMING
# --------------------------------------------------

def find_optimal_strategy():

    # State:
    # (fuel remaining, tyre age)
    #
    # Candidate:
    # (total time, starting fuel, pit stops)
    #
    # Only the fastest candidate is kept for each state.

    states = {}

    # Starting fuel must be a whole number of litres

    minimum_starting_fuel = math.ceil(fuel_consumption)

    for starting_fuel in range(
        minimum_starting_fuel,
        max_tank + 1
    ):

        states[(round(float(starting_fuel), 6), 0)] = (
            0.0,
            starting_fuel,
            []
        )

    # Process each lap

    for lap in range(1, race_laps + 1):

        new_states = {}

        def store_state(fuel, tyre_age, candidate):

            key = (round(fuel, 6), tyre_age)

            if (
                key not in new_states
                or candidate[0] < new_states[key][0]
            ):
                new_states[key] = candidate

        for (fuel, tyre_age), candidate in states.items():

            total_time, starting_fuel, pit_stops = candidate

            # --------------------------------------------------
            # OPTION 1: DO NOT PIT
            # --------------------------------------------------

            if fuel >= fuel_consumption - 0.000001:

                lap_time = calculate_lap_time(
                    fuel,
                    tyre_age
                )

                remaining_fuel = round(
                    fuel - fuel_consumption,
                    6
                )

                new_candidate = (
                    total_time + lap_time,
                    starting_fuel,
                    pit_stops
                )

                store_state(
                    remaining_fuel,
                    tyre_age + 1,
                    new_candidate
                )

            # --------------------------------------------------
            # OPTION 2: PIT BEFORE THIS LAP
            # --------------------------------------------------

            if lap > 1:

                max_fuel_addition = math.floor(
                    max_tank - fuel + 0.000001
                )

                for fuel_added in range(
                    0,
                    max_fuel_addition + 1
                ):

                    for change_tyres in [False, True]:

                        # Skip a stop that does nothing

                        if fuel_added == 0 and not change_tyres:
                            continue

                        fuel_after_pit = fuel + fuel_added

                        # Check enough fuel for the next lap

                        if (
                            fuel_after_pit
                            < fuel_consumption - 0.000001
                        ):
                            continue

                        pit_time = calculate_pit_time(
                            fuel_added,
                            change_tyres
                        )

                        new_tyre_age = (
                            0 if change_tyres else tyre_age
                        )

                        lap_time = calculate_lap_time(
                            fuel_after_pit,
                            new_tyre_age
                        )

                        remaining_fuel = round(
                            fuel_after_pit - fuel_consumption,
                            6
                        )

                        new_pit_stops = pit_stops + [
                            (
                                lap - 1,
                                fuel_added,
                                change_tyres
                            )
                        ]

                        new_candidate = (
                            total_time + pit_time + lap_time,
                            starting_fuel,
                            new_pit_stops
                        )

                        store_state(
                            remaining_fuel,
                            new_tyre_age + 1,
                            new_candidate
                        )

        states = new_states

        if not states:
            return None

    # Find the fastest finishing candidate

    if not states:
        return None

    best_candidate = min(
        states.values(),
        key=lambda candidate: candidate[0]
    )

    _, starting_fuel, pit_stops = best_candidate

    return {
        "name": "Optimal Strategy",
        "starting_fuel": starting_fuel,
        "pit_stops": pit_stops
    }


# --------------------------------------------------
# CALCULATE OPTIMAL STRATEGY
# --------------------------------------------------

if st.session_state.optimal_strategy is None:

    with st.spinner("Calculating optimal strategy..."):

        st.session_state.optimal_strategy = (
            find_optimal_strategy()
        )

optimal_strategy = st.session_state.optimal_strategy


if optimal_strategy is None:
    st.error(
        "No valid strategy found. Check your fuel consumption "
        "and tank capacity."
    )
    st.stop()


# --------------------------------------------------
# SIMULATE OPTIMAL STRATEGY
# --------------------------------------------------

optimal_result = simulate_strategy(
    optimal_strategy["starting_fuel"],
    optimal_strategy["pit_stops"]
)

if optimal_result is None:
    st.error("Unable to simulate the optimal strategy.")
    st.stop()

optimal_strategy["total_time"] = optimal_result["total_time"]


# --------------------------------------------------
# DISPLAY OPTIMAL STRATEGY
# --------------------------------------------------

st.divider()
st.header("Optimal Strategy")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Total Race Time",
    f"{optimal_result['total_time']:.2f} s"
)

col2.metric(
    "Starting Fuel",
    f"{optimal_strategy['starting_fuel']} L"
)

col3.metric(
    "Pit Stops",
    len(optimal_strategy["pit_stops"])
)

st.subheader("Pit Stop Details")

if optimal_strategy["pit_stops"]:

    for lap, fuel_added, change_tyres in optimal_strategy["pit_stops"]:

        tyre_text = (
            "Change tyres"
            if change_tyres
            else "Keep tyres"
        )

        st.write(
            f"After lap **{lap}**: "
            f"Add **{fuel_added} L** – {tyre_text}"
        )

else:
    st.write("No pit stops required.")


# --------------------------------------------------
# CUSTOM STRATEGY INPUT
# --------------------------------------------------

st.divider()
st.header("Add Custom Strategy")

with st.expander("Create a custom strategy"):

    strategy_name = st.text_input(
        "Strategy name",
        placeholder="e.g. Two-stop strategy"
    )

    starting_fuel = st.number_input(
        "Starting fuel (L)",
        min_value=1,
        max_value=max_tank,
        value=None,
        step=1,
        placeholder="Enter starting fuel"
    )

    st.write("Enter pit stops in the following format:")

    st.code(
        "after lap, fuel added (L), change tyres (yes/no)\n"
        "10, 25, yes\n"
        "25, 15, no"
    )

    pit_stop_input = st.text_area(
        "Pit stops",
        placeholder="10, 25, yes\n25, 15, no"
    )

    if st.button("Add Strategy", type="primary"):

        if starting_fuel is None:

            st.error("Please enter starting fuel.")

        elif not strategy_name.strip():

            st.error("Please enter a strategy name.")

        else:

            parsed_pit_stops = []
            used_laps = set()
            valid = True

            if pit_stop_input.strip():

                for line in pit_stop_input.strip().splitlines():

                    try:

                        parts = [
                            part.strip()
                            for part in line.split(",")
                        ]

                        if len(parts) != 3:
                            raise ValueError

                        pit_lap = int(parts[0])
                        fuel_added = int(parts[1])
                        tyre_choice = parts[2].lower()

                        if tyre_choice not in ["yes", "no"]:
                            raise ValueError

                        if not 1 <= pit_lap < race_laps:
                            raise ValueError

                        if fuel_added < 0:
                            raise ValueError

                        if pit_lap in used_laps:
                            raise ValueError

                        if fuel_added == 0 and tyre_choice == "no":
                            raise ValueError

                        used_laps.add(pit_lap)

                        parsed_pit_stops.append(
                            (
                                pit_lap,
                                fuel_added,
                                tyre_choice == "yes"
                            )
                        )

                    except ValueError:

                        st.error(
                            f"Invalid pit stop entry: {line}"
                        )

                        valid = False
                        break

            parsed_pit_stops.sort(key=lambda stop: stop[0])

            if valid:

                result = simulate_strategy(
                    starting_fuel,
                    parsed_pit_stops
                )

                if result is None:

                    st.error(
                        "This strategy is not possible. "
                        "Check fuel levels and tank capacity."
                    )

                else:

                    strategy_id = st.session_state.next_custom_id

                    st.session_state.custom_strategies.append({
                        "id": strategy_id,
                        "name": strategy_name.strip(),
                        "starting_fuel": int(starting_fuel),
                        "pit_stops": parsed_pit_stops
                    })

                    st.session_state.next_custom_id += 1

                    st.rerun()


# --------------------------------------------------
# STRATEGY COMPARISON
# --------------------------------------------------

st.divider()
st.header("Strategy Comparison")

all_strategies = []

# Add optimal strategy

all_strategies.append({
    "id": "optimal",
    "name": "Optimal Strategy",
    "starting_fuel": optimal_strategy["starting_fuel"],
    "pit_stops": optimal_strategy["pit_stops"],
    "is_optimal": True
})

# Add custom strategies

for strategy in st.session_state.custom_strategies:

    all_strategies.append({
        "id": strategy["id"],
        "name": strategy["name"],
        "starting_fuel": strategy["starting_fuel"],
        "pit_stops": strategy["pit_stops"],
        "is_optimal": False
    })


# Simulate all strategies

for strategy in all_strategies:

    result = simulate_strategy(
        strategy["starting_fuel"],
        strategy["pit_stops"]
    )

    strategy["result"] = result

    if result is not None:
        strategy["total_time"] = result["total_time"]
        strategy["cumulative_times"] = result["cumulative_times"]
        strategy["lap_times"] = result["lap_times"]


# Find fastest strategy

valid_strategies = [
    strategy
    for strategy in all_strategies
    if strategy["result"] is not None
]

fastest_time = min(
    strategy["total_time"]
    for strategy in valid_strategies
)


# --------------------------------------------------
# DISPLAY COMPARISON CARDS
# --------------------------------------------------

visible_strategies = []

for strategy in all_strategies:

    st.subheader(strategy["name"])

    if strategy["result"] is None:

        st.error("Invalid strategy.")
        continue

    delta = strategy["total_time"] - fastest_time

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Race Time",
        f"{strategy['total_time']:.2f} s"
    )

    col2.metric(
        "Difference to Fastest",
        f"+{delta:.2f} s" if delta > 0 else "Fastest"
    )

    col3.metric(
        "Starting Fuel",
        f"{strategy['starting_fuel']} L"
    )

    col4.metric(
        "Pit Stops",
        len(strategy["pit_stops"])
    )

    if strategy["pit_stops"]:

        pit_descriptions = []

        for lap, fuel_added, change_tyres in strategy["pit_stops"]:

            tyre_text = "New tyres" if change_tyres else "Old tyres"

            pit_descriptions.append(
                f"Lap {lap}: +{fuel_added} L, {tyre_text}"
            )

        st.caption(" | ".join(pit_descriptions))

    else:

        st.caption("No pit stops")

    col1, col2 = st.columns([3, 1])

    with col1:

        show_strategy = st.checkbox(
            "Show on graphs",
            value=True,
            key=f"show_{strategy['id']}"
        )

        if show_strategy:
            visible_strategies.append(strategy)

    with col2:

        if not strategy["is_optimal"]:

            if st.button(
                "Delete",
                key=f"delete_{strategy['id']}"
            ):

                st.session_state.custom_strategies = [
                    item
                    for item in st.session_state.custom_strategies
                    if item["id"] != strategy["id"]
                ]

                st.rerun()

    st.divider()


# --------------------------------------------------
# CUMULATIVE RACE TIME GRAPH
# --------------------------------------------------

st.header("Cumulative Race Time")

if visible_strategies:

    cumulative_data = {}

    for strategy in visible_strategies:

        cumulative_data[strategy["name"]] = (
            strategy["cumulative_times"]
        )

    cumulative_df = pd.DataFrame(
        cumulative_data,
        index=range(0, race_laps + 1)
    )

    cumulative_df.index.name = "Lap"

    st.line_chart(
        cumulative_df,
        x_label="Lap",
        y_label="Cumulative time (seconds)"
    )

else:

    st.info("Select at least one strategy to display the graph.")


# --------------------------------------------------
# INDIVIDUAL LAP TIME GRAPH
# --------------------------------------------------

st.header("Individual Lap Times")

if visible_strategies:

    lap_time_data = {}

    for strategy in visible_strategies:

        lap_time_data[strategy["name"]] = (
            strategy["lap_times"]
        )

    lap_time_df = pd.DataFrame(
        lap_time_data,
        index=range(1, race_laps + 1)
    )

    lap_time_df.index.name = "Lap"

    st.line_chart(
        lap_time_df,
        x_label="Lap",
        y_label="Lap time (seconds)"
    )

    st.caption(
        "Individual lap times exclude pit-stop time. "
        "The effect of refuelling and tyre changes is reflected "
        "in the laps following each stop."
    )

else:

    st.info("Select at least one strategy to display the graph.")


# --------------------------------------------------
# HELP
# --------------------------------------------------

with st.expander("How the optimiser works"):

    st.write("""
    **Lap time model**

    Lap time is calculated using:

    Lap time = Base lap time
    + Fuel penalty
    + Tyre degradation

    Fuel is tracked in litres, but the fuel penalty is
    measured per lap of fuel. The current fuel load is
    therefore divided by fuel consumption to calculate
    the number of laps of fuel remaining.

    **Pit stops**

    Pit-stop time is calculated as:

    Pit lane loss + max(refuelling time, tyre change time)

    Refuelling and tyre changes happen simultaneously.

    Fuel additions and starting fuel must be whole litres.
    Fuel consumption can be fractional.

    **Optimisation**

    The optimiser uses dynamic programming to find the
    fastest strategy. It keeps the fastest candidate for
    each combination of remaining fuel and tyre age.

    Custom strategies can be added to compare different
    pit-stop approaches against the optimum.

    **Graphs**

    The cumulative race-time graph includes pit-stop time.

    The individual lap-time graph shows the time taken
    to complete each lap, excluding pit-stop time.
    """)
