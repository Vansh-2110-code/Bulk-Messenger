"""
Helper script to create sample contacts.xlsx file
Run this to create a template Excel file with sample data
"""

import pandas as pd

# Sample data
data = {
    'Name': ['John Doe', 'Jane Smith', 'Mike Johnson'],
    'Email': ['john@example.com', 'jane@example.com', 'mike@example.com'],
    'Phone': ['+919876543210', '+919876543211', '+919876543212']
}

df = pd.DataFrame(data)
df.to_excel('contacts.xlsx', index=False)

print("✅ Sample contacts.xlsx created successfully!")
print("\nSample data:")
print(df)
print("\n⚠️  Remember to replace this data with your actual contacts!")
