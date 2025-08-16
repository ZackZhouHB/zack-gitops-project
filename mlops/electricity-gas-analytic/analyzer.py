import pandas as pd
import json
import numpy as np

def load_and_process_data(electricity_file, gas_file):
    """Loads, merges, and preprocesses the electricity and gas data."""
    try:
        elec_df = pd.read_csv(electricity_file)
        gas_df = pd.read_csv(gas_file)
    except FileNotFoundError as e:
        print(f"Error: {e}. Make sure the input files are in the correct directory.")
        return None

    elec_df.columns = ['consumption_kwh', 'cost_c', 'start', 'end']
    gas_df.columns = ['consumption_kwh', 'cost_c', 'start', 'end']
    elec_df['type'] = 'electricity'
    gas_df['type'] = 'gas'
    df = pd.concat([elec_df, gas_df], ignore_index=True)
    df['start'] = pd.to_datetime(df['start'])
    df['end'] = pd.to_datetime(df['end'])
    df['hour'] = df['start'].dt.hour
    df['day_of_week'] = df['start'].dt.dayofweek # Monday=0, Sunday=6
    df['date'] = df['start'].dt.date.astype(str)
    return df

def get_key_metrics(df):
    """Calculates key performance indicators for the data overview."""
    total_consumption = df.groupby('type')['consumption_kwh'].sum().to_dict()
    total_cost = df.groupby('type')['cost_c'].sum().to_dict()
    return {
        'total_consumption_kwh': total_consumption,
        'total_cost_c': total_cost,
        'average_daily_consumption_kwh': {
            'electricity': df[df['type'] == 'electricity'].groupby('date')['consumption_kwh'].sum().mean(),
            'gas': df[df['type'] == 'gas'].groupby('date')['consumption_kwh'].sum().mean(),
        }
    }

def get_consumption_trends_data(df):
    """Prepares data for the Consumption Trends tab."""
    # Hourly Average
    hourly_avg = df.groupby(['hour', 'type'])['consumption_kwh'].mean().unstack(fill_value=0)
    hourly_data = {
        'electricity': hourly_avg['electricity'].reindex(range(24), fill_value=0).tolist(),
        'gas': hourly_avg['gas'].reindex(range(24), fill_value=0).tolist(),
    }

    # Weekly Average
    weekly_avg = df.groupby(['day_of_week', 'type'])['consumption_kwh'].mean().unstack(fill_value=0)
    weekly_data = {
        'electricity': weekly_avg['electricity'].reindex(range(7), fill_value=0).tolist(),
        'gas': weekly_avg['gas'].reindex(range(7), fill_value=0).tolist(),
    }
    
    return {
        'hourly_avg': hourly_data,
        'weekly_avg': weekly_data
    }

def get_cost_analysis_data(df):
    """Prepares data for the Cost Analysis tab."""
    # Cost Composition
    cost_composition_c = df.groupby('type')['cost_c'].sum().to_dict()

    # Daily Cost Trend
    daily_cost = df.groupby(['date', 'type'])['cost_c'].sum().unstack(fill_value=0)
    daily_cost['total'] = daily_cost.sum(axis=1)
    daily_cost = daily_cost.sort_index()
    
    daily_cost_trend = {
        'labels': daily_cost.index.tolist(),
        'total': daily_cost['total'].tolist(),
        'gas': daily_cost['gas'].tolist(),
        'electricity': daily_cost['electricity'].tolist(),
    }
    
    return {
        'cost_composition_c': cost_composition_c,
        'daily_cost_trend': daily_cost_trend
    }

def get_usage_patterns_data(df):
    """Prepares data for the Usage Patterns tab."""
    # Hourly and Weekly averages can be reused from consumption trends
    consumption_trends = get_consumption_trends_data(df)

    # Radar Chart Data
    # Using time of day segments for the radar chart
    def get_time_of_day(hour):
        if 5 <= hour < 12: return 'Morning'
        if 12 <= hour < 17: return 'Afternoon'
        if 17 <= hour < 21: return 'Evening'
        return 'Night'
    
    df['time_of_day'] = df['hour'].apply(get_time_of_day)
    radar_avg = df.groupby(['time_of_day', 'type'])['consumption_kwh'].mean().unstack(fill_value=0)
    radar_labels = ['Morning', 'Afternoon', 'Evening', 'Night']
    radar_data = {
        'labels': radar_labels,
        'electricity': radar_avg['electricity'].reindex(radar_labels, fill_value=0).tolist(),
        'gas': radar_avg['gas'].reindex(radar_labels, fill_value=0).tolist(),
    }

    # Peak Times
    hourly_avg_df = df.groupby(['hour', 'type'])['consumption_kwh'].mean().reset_index()
    peak_elec = hourly_avg_df.loc[hourly_avg_df[hourly_avg_df['type'] == 'electricity']['consumption_kwh'].idxmax()]
    peak_gas = hourly_avg_df.loc[hourly_avg_df[hourly_avg_df['type'] == 'gas']['consumption_kwh'].idxmax()]
    peak_times = {
        'electricity': {'hour': int(peak_elec['hour']), 'consumption': float(peak_elec['consumption_kwh'])},
        'gas': {'hour': int(peak_gas['hour']), 'consumption': float(peak_gas['consumption_kwh'])},
    }

    return {
        'hourly_avg': consumption_trends['hourly_avg'],
        'weekly_avg': consumption_trends['weekly_avg'],
        'radar_data': radar_data,
        'peak_times': peak_times
    }

def get_savings_potential(df):
    """Assesses potential savings based on usage patterns."""
    hourly_avg = df.groupby(['hour', 'type'])['consumption_kwh'].mean().reset_index()
    peak_hours = hourly_avg.loc[hourly_avg.groupby('type')['consumption_kwh'].idxmax()]
    off_peak_hours = hourly_avg.loc[hourly_avg.groupby('type')['consumption_kwh'].idxmin()]
    
    potential_savings = {}
    for energy_type in ['electricity', 'gas']:
        peak_data = peak_hours[peak_hours['type'] == energy_type]
        off_peak_data = off_peak_hours[off_peak_hours['type'] == energy_type]
        
        if not peak_data.empty and not off_peak_data.empty:
            peak_hour = peak_data.iloc[0]['hour']
            off_peak_hour = off_peak_data.iloc[0]['hour']
            peak_cost_per_unit = 1.0
            off_peak_cost_per_unit = 0.8
            daily_peak_consumption = df[(df['hour'] == peak_hour) & (df['type'] == energy_type)]['consumption_kwh'].sum()
            potential_shift = daily_peak_consumption * 0.2
            daily_savings_cents = potential_shift * (peak_cost_per_unit - off_peak_cost_per_unit) * 100
            monthly_savings_cents = daily_savings_cents * 30
            potential_savings[energy_type] = {
                'peak_hour': int(peak_hour),
                'off_peak_hour': int(off_peak_hour),
                'potential_daily_shift_kwh': float(potential_shift),
                'potential_monthly_savings_cents': float(monthly_savings_cents),
                'potential_monthly_savings_dollars': float(monthly_savings_cents / 100)
            }
    
    total_potential_savings = sum(item['potential_monthly_savings_dollars'] for item in potential_savings.values())

    return {
        'potential_savings': potential_savings,
        'total_potential_savings': total_potential_savings,
        'recommendations': [
            "Consider shifting non-essential energy usage to off-peak hours",
            "Use programmable thermostats to optimize heating schedules",
            "Run major appliances during off-peak hours when possible",
            "Consider energy-efficient appliances to reduce overall consumption"
        ]
    }

def main():
    """Main function to run the analysis and save results for the frontend."""
    electricity_file = 'electricity_consumption_2months_patterned.csv'
    gas_file = 'gas_consumption_2months_patterned.csv'

    df = load_and_process_data(electricity_file, gas_file)
    if df is None:
        return

    # Generate data for each frontend component
    key_metrics = get_key_metrics(df)
    consumption_trends = get_consumption_trends_data(df)
    cost_analysis = get_cost_analysis_data(df)
    usage_patterns = get_usage_patterns_data(df)
    savings = get_savings_potential(df)

    # Combine results into a single dictionary matching frontend expectations
    analysis_results = {
        "data_overview": key_metrics,
        "consumption_trends": consumption_trends,
        "cost_analysis": cost_analysis,
        "usage_patterns": usage_patterns,
        "savings_potential": savings,
        "raw_data_timeseries": df.to_dict('records')
    }

    # Save results to a JSON file
    try:
        with open('analysis_results.json', 'w') as f:
            json.dump(analysis_results, f, indent=4, default=str)
        print("Analysis complete. Results saved to analysis_results.json")
        
        # Also copy to the public folder for the frontend to fetch
        with open('client/public/analysis_results.json', 'w') as f:
            json.dump(analysis_results, f, indent=4, default=str)
        print("Copied analysis_results.json to client/public/")

    except IOError as e:
        print(f"Error writing to file: {e}")

if __name__ == '__main__':
    main()