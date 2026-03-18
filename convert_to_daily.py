import pandas as pd
import os

def convert_5min_to_daily(input_file, output_file):
    """
    Convert 5-minute stock data to daily data
    """
    print(f"Processing {input_file}...")
    
    # Read the 5-minute data
    df = pd.read_csv(input_file)
    
    # Convert date column to datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Extract date part (without time)
    df['trading_date'] = df['date'].dt.date
    
    # Group by trading date and aggregate
    daily_data = df.groupby('trading_date').agg({
        'open': 'first',           # First open price of the day
        'high': 'max',             # Highest price of the day
        'low': 'min',              # Lowest price of the day
        'close': 'last',           # Last close price of the day
        'volume': 'sum'            # Total volume for the day
    }).reset_index()
    
    # Rename the date column
    daily_data.rename(columns={'trading_date': 'date'}, inplace=True)
    
    # Convert date back to string format
    daily_data['date'] = daily_data['date'].astype(str)
    
    # Sort by date
    daily_data = daily_data.sort_values('date')
    
    # Save to CSV
    daily_data.to_csv(output_file, index=False)
    print(f"Created {output_file} with {len(daily_data)} daily records")
    
    return daily_data

def main():
    # List of files to process
    files_to_process = [
        'LT_5minute.csv',
        'TITAN_5minute.csv', 
        'ULTRACEMCO_5minute.csv'
    ]
    
    # Process each file
    for filename in files_to_process:
        input_path = filename
        output_path = filename.replace('_5minute.csv', '_daily.csv')
        
        if os.path.exists(input_path):
            try:
                convert_5min_to_daily(input_path, output_path)
                print(f"✓ Successfully converted {filename} to daily data\n")
            except Exception as e:
                print(f"✗ Error processing {filename}: {e}\n")
        else:
            print(f"✗ File {filename} not found\n")

if __name__ == "__main__":
    main()
