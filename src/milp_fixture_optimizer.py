import pulp
import pandas as pd

# ==========================================================
# 1. FIXTURE DATABASE (From Paper: Table 2.4.1 & Table 3.3.1)
# ==========================================================
# Water consumption is in Liters per person per day (LPCD)
# Baseline and Design fixtures with their costs and unit quantities
fixtures_data = {
    'Water Closet': [
        {'name': 'Baseline Dual Push (6L/3L)', 'cost': 714, 'units': 650, 'daily_lpcd': 12.0},
        {'name': 'Jaquar Metropole Low-Flow (4L/2L)', 'cost': 2760, 'units': 650, 'daily_lpcd': 8.0}
    ],
    'Health Faucet / Bidet': [
        {'name': 'Lifelong Standard (6 LPM)', 'cost': 578, 'units': 650, 'daily_lpcd': 1.5},
        {'name': 'Hindware + Eco Aerator (3 LPM)', 'cost': 1120, 'units': 650, 'daily_lpcd': 0.75}
    ],
    'Faucet': [
        {'name': 'Clinton Brass Bib Cock (6 LPM)', 'cost': 449, 'units': 650, 'daily_lpcd': 12.0},
        {'name': 'Hindware + Eco Aerator (3 LPM)', 'cost': 889, 'units': 650, 'daily_lpcd': 6.0}
    ],
    'Kitchen Sink': [
        {'name': 'Jagger Standard (6 LPM)', 'cost': 649, 'units': 320, 'daily_lpcd': 9.0},
        {'name': 'Hindware Sink Cock + Aerator (3 LPM)', 'cost': 1540, 'units': 320, 'daily_lpcd': 4.5}
    ],
    'Showerhead': [
        {'name': 'Johnson Hand Shower (10 LPM)', 'cost': 1120, 'units': 650, 'daily_lpcd': 80.0},
        {'name': 'Jaquar Airshower (6 LPM)', 'cost': 3000, 'units': 650, 'daily_lpcd': 48.0}
    ]
}

# Total occupants (regular + caretakers + shopkeepers + guests)
TOTAL_OCCUPANTS = 2813
FIXED_POTABLE_WATER_LPCD = 20.0  # Fixed 20 LPCD non-negotiable drinking water
DAYS_IN_YEAR = 365

# ==========================================================
# 2. OPTIMIZATION FUNCTION
# ==========================================================
def optimize_water_consumption(budget_limit):
    # Initialize LP Problem
    model = pulp.LpProblem("Minimize_Water_Consumption", pulp.LpMinimize)

    # Decision variables: x[(category, option_idx)] in {0, 1}
    x = {}
    for cat, options in fixtures_data.items():
        for j in range(len(options)):
            x[(cat, j)] = pulp.LpVariable(f"choice_{cat.replace(' ', '_')}_{j}", cat='Binary')

    # 1. Selection Constraint: Choose exactly one fixture option per category
    for cat, options in fixtures_data.items():
        model += pulp.lpSum([x[(cat, j)] for j in range(len(options))]) == 1

    # 2. Budget Constraint: Total cost of selected fixtures <= budget_limit
    total_cost = pulp.lpSum([
        options[j]['cost'] * options[j]['units'] * x[(cat, j)]
        for cat, options in fixtures_data.items()
        for j in range(len(options))
    ])
    model += total_cost <= budget_limit

    # 3. Objective Function: Minimize Total Annual Water Consumption (in Liters)
    daily_fixture_lpcd = pulp.lpSum([
        options[j]['daily_lpcd'] * x[(cat, j)]
        for cat, options in fixtures_data.items()
        for j in range(len(options))
    ])
    
    # Total consumption = (Fixture LPCD + Fixed LPCD) * Occupants * 365
    annual_water_consumption = (daily_fixture_lpcd + FIXED_POTABLE_WATER_LPCD) * TOTAL_OCCUPANTS * DAYS_IN_YEAR
    model += annual_water_consumption

    # Solve model
    model.solve(pulp.PULP_CBC_CMD(msg=False))

    if pulp.LpStatus[model.status] == 'Optimal':
        chosen_fixtures = []
        for cat, options in fixtures_data.items():
            for j in range(len(options)):
                if pulp.value(x[(cat, j)]) > 0.5:
                    chosen_fixtures.append({
                        'Category': cat,
                        'Selected Fixture': options[j]['name'],
                        'Unit Cost (₹)': options[j]['cost'],
                        'Units': options[j]['units'],
                        'Total Cost (₹)': options[j]['cost'] * options[j]['units'],
                        'Water Use (LPCD)': options[j]['daily_lpcd']
                    })

        return {
            'status': 'Optimal',
            'annual_water_liters': pulp.value(annual_water_consumption),
            'daily_per_capita_liters': pulp.value(daily_fixture_lpcd) + FIXED_POTABLE_WATER_LPCD,
            'total_cost': pulp.value(total_cost),
            'selected_fixtures': chosen_fixtures
        }
    else:
        return {'status': 'Infeasible'}

# ==========================================================
# 3. RUN SAMPLE OPTIMIZATION
# ==========================================================
# Set a budget threshold (e.g., ₹4,000,000)
BUDGET = 4000000 

result = optimize_water_consumption(BUDGET)

if result['status'] == 'Optimal':
    print(f"--- OPTIMIZATION RESULT (Budget: ₹{BUDGET:,.2f}) ---")
    print(f"Total Fixture Investment: ₹{result['total_cost']:,.2f}")
    print(f"Daily Demand per Capita:  {result['daily_per_capita_liters']:.2f} L/person/day")
    print(f"Annual Water Consumption: {result['annual_water_liters'] / 1e6:.2f} Megaliters/year")
    print("\nOptimal Fixture Selection:")
    df_fixtures = pd.DataFrame(result['selected_fixtures'])
    print(df_fixtures[['Category', 'Selected Fixture', 'Total Cost (₹)', 'Water Use (LPCD)']].to_string(index=False))
else:
    print(f"No feasible fixture combination within ₹{BUDGET:,.2f}.")