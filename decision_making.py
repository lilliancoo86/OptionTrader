import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.impute import SimpleImputer
import matplotlib.pyplot as plt
import numpy as np

# Load the training data from Excel file
train_data = pd.read_excel('data.xlsx')

# Preprocess the training data
train_data['Earnings_Date'] = pd.to_datetime(train_data['Earnings_Date'])
train_data['Buy_Date'] = pd.to_datetime(train_data['Buy_Date'])
train_data['Sell_Date'] = pd.to_datetime(train_data['Sell_Date'])
train_data['Gain'] = train_data['Total_Gain'] > 0

# Select features for training (excluding Gain and date columns)
train_features = ['Current_Price', 'Call_Strike', 'Put_Strike', 'Buy_Call_Price', 'Buy_Put_Price',
                  'Call_Volume', 'Call_Open_Interest', 'Put_Volume', 'Put_Open_Interest']

X_train = train_data[train_features]
y_train = train_data['Gain']

# Handle missing values by imputing with the mean
imputer = SimpleImputer(strategy='mean')
X_train = imputer.fit_transform(X_train)

# Split the training data into training and testing sets
X_train_split, X_test_split, y_train_split, y_test_split = train_test_split(X_train, y_train, test_size=0.2, random_state=42)

# Train the Gradient Boosting model
model = GradientBoostingClassifier(n_estimators=100, random_state=42)
model.fit(X_train_split, y_train_split)
y_pred_split = model.predict(X_test_split)

# Print the training results
accuracy = accuracy_score(y_test_split, y_pred_split)
print(f'Accuracy: {accuracy:.2f}')
print(classification_report(y_test_split, y_pred_split))

# Feature importance for the model
importances = model.feature_importances_
feature_importance = pd.Series(importances, index=train_features)
plt.figure(figsize=(12, 8))
feature_importance.sort_values(ascending=False).plot(kind='bar')
plt.title('Feature Importance')
plt.tight_layout()
plt.show()

# Load the new data for prediction from options_data.xlsx
new_data = pd.read_excel('options_data.xlsx')

# Inspect the columns of the new data
print("Columns in new data:", new_data.columns)

# Rename the columns to match those used during training
new_data.rename(columns={
    'call_strike': 'Call_Strike',
    'put_strike': 'Put_Strike',
    'call_premium': 'Buy_Call_Price',
    'put_premium': 'Buy_Put_Price',
    'call_volume': 'Call_Volume',
    'call_open_interest': 'Call_Open_Interest',
    'put_volume': 'Put_Volume',
    'put_open_interest': 'Put_Open_Interest',
    'current_price': 'Current_Price',  # Ensure this matches exactly
    'call_put_ratio': 'Call_Put_Ratio'
}, inplace=True)

# Ensure all necessary columns are present
new_features = ['Current_Price', 'Call_Strike', 'Put_Strike', 'Buy_Call_Price', 'Buy_Put_Price',
                'Call_Volume', 'Call_Open_Interest', 'Put_Volume', 'Put_Open_Interest']

# Check for missing columns
missing_cols = [col for col in new_features if col not in new_data.columns]
if missing_cols:
    raise KeyError(f"Missing columns in new data: {missing_cols}")

new_X = new_data[new_features]
new_X = imputer.transform(new_X)

# Make predictions on the new data
new_data['Predicted_Gain'] = model.predict(new_X)

# Save the new data with predictions to an Excel file
new_data.to_excel('predicted_options_data.xlsx', engine='xlsxwriter', index=False)

print(new_data)
