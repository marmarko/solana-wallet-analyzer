import pandas as pd

def copy_rows(input_file, output_file):
    # Read the Excel file
    xls = pd.ExcelFile(input_file)
    df_output = pd.DataFrame()
    #add header row to df_output
    predefined_columns = ['Wallet', 'ROI Realized', 'PnL Realized', 'WinRate', 'Total Fees', 'SOL Price', 'Balance', 'Not Swap Tx', 'Scam', 'Tokens']
    
    df_output = pd.DataFrame(columns=predefined_columns)

    for sheet_name in xls.sheet_names:
        # Read the sheet into a DataFrame
        df = pd.read_excel(xls, sheet_name=sheet_name)
        
        # Copy only the third row but just the first 5 columns
        df_third_row = df.iloc[1:2, :10]
        df_third_row.columns = predefined_columns
        
        # add the row to the output DataFrame under the columns defined in the header
        df_output = pd.concat([df_output, df_third_row], ignore_index=True)

    # Save the output DataFrame to a csv file
    df_output.to_excel(output_file, index=False)

if __name__ == "__main__":
    input_file = 'input.xlsx'  # Replace with your input file path
    output_file = 'output.xlsx'  # Replace with your desired output file path
    copy_rows(input_file, output_file)