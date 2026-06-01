import pandas as pd

forecasted_results_df = pd.read_csv("forecast.csv")
print(forecasted_results_df.head())

real_data_df = pd.read_csv("NQ_4h_2026.csv")
print(real_data_df.head())

evaluation_df = pd.DataFrame()
evaluation_df["Error"] = real_data_df["close"] - forecasted_results_df["yhat"]
evaluation_df["Absolute Error"] = evaluation_df["Error"].abs()
evaluation_df["Squared Error"] = evaluation_df["Error"] ** 2   
evaluation_df["RMSE"] = evaluation_df["Squared Error"].mean() ** 0.5
evaluation_df["MAE"] = evaluation_df["Absolute Error"].mean()
print(evaluation_df.head())
print(f"Root Mean Squared Error (RMSE): {evaluation_df['RMSE'].iloc[0]}")
print(f"Mean Absolute Error (MAE): {evaluation_df['MAE'].iloc[0]}") 

evaluation_df.to_csv("evaluation_results.csv", index=False)