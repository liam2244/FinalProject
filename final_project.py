"""
Name:       Liam Hill
CS230:      Section 4
Data:       NY-House_Dataset.csv
URL:        https://finalproject-7nbwnwgksxzfikygzftm9c.streamlit.app


Description:

This program uses data from the New York housing market to allow potential buyers to navigate and filter through the countless listings
easily and displays many useful calculations, graphs, and bits of information.
"""

#Import all necessary packages
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sea
import pydeck as pdk

# [PY3] Error handling with try/except when loading CSV
try: #try loading the housing dataset
    df = pd.read_csv("NY-House-Dataset.csv")
except Exception as e: #display an error message if incorrect
    st.error(f"Error loading data: {e}")

df.columns = df.columns.str.strip() #Remove extra spaces from column names

# [DA1] Clean: Drop all rows missing price or sublocality values
df.dropna(subset=["PRICE", "SUBLOCALITY"], inplace=True)

# Print title
st.title("NY Housing Data Tool")

# [CHART1] Bar chart: Create and display bar chart showing average price by area
with st.expander("View Average Prices by Area", expanded=False): #See section 4 of document
    st.subheader("Average Home Price by Area")
    st.caption("This chart shows the average listing price in each sublocality, sorted high to low.")
    grouped = df.groupby("SUBLOCALITY") #group the data by sublocality
    average_prices = grouped["PRICE"].mean() #Find the mean price of each group,
    avg_prices = average_prices.sort_values(ascending=False) #Sort from high to low
    avg_prices.plot(kind="bar", color="orange", edgecolor="black", linewidth=0.7) #Use average prices to plot on bar chart
    plt.title("Average Price by Area", fontsize=16, weight="bold")
    plt.ylabel("Average Price ($)", fontsize=12)
    plt.xlabel("Area", fontsize=12)
    plt.ticklabel_format(style='plain', axis='y')  # keeps real number formatting on y-axis
    st.pyplot(plt.gcf())
    plt.clf()

# [ST1] Widget: Dropdown to select sublocality
areas = sorted(df["SUBLOCALITY"].unique()) #Find all unique sublocalities
st.sidebar.title("Search Filters")
selected_area = st.sidebar.selectbox("Choose an area:", areas)


# Filter dataset to selected area for price slider
area_df = df[df["SUBLOCALITY"] == selected_area]

# [PY5] Show number of listings by type for the specified area
type_counts = dict(area_df["TYPE"].value_counts()) #Create a dictionary of the counts for each type
st.sidebar.markdown("**Available Home Types in This Area:**") #Print header
for home_type, count in type_counts.items(): #Display results if there is 1 or more of the type
    st.sidebar.write(f"{home_type}: {count} listing{'s' if count != 1 else ''}")

# [PY2] Function that returns min and max price for a specified area, later used for min and max slider values (See section 1 of document)
def get_price_range(area_df):
    min_val = int(area_df["PRICE"].min()) #Get min and max from sorted area_df
    max_val = int(area_df["PRICE"].max())
    if min_val == max_val: #If there is only one listing for the area, the maximum is increased to avoid an error
        max_val += 10000
    return min_val, max_val #Return values for use

# [ST2] Widget: Slider to set desired max price
min_price, max_price = get_price_range(area_df) #Use function from above to get range
price_limit = st.sidebar.slider("Set your max price:", min_value=min_price, max_value=max_price, value=max_price, step=10000, format="$%d") #Create slider and assign it to a variable to call on later, format is from chatGPT

# [ST3] Widget: Multiselect for home types, default to top 3 most common if they exist
home_types = sorted(area_df["TYPE"].dropna().unique()) #Find all the unique home types for the area
type_counts = area_df["TYPE"].value_counts() #Count how many times each home type appears
type_counts_sorted = list(type_counts.index) #sort the index(type name) based on the values(counts) associated with them

default_types = type_counts_sorted[:3] if len(type_counts_sorted) >= 3 else type_counts_sorted #if there are more than three types, the most popular are the defaults, otherwise they are all defaults

selected_types = st.sidebar.multiselect("Choose home type(s):", home_types, default=default_types) #Make a multiselect box with default values and assign it to a variable


# [DA5], [DA2], [DA4] — Apply all filters to new dataframe to display it
specific_filtered_df = df[
    (df["SUBLOCALITY"] == selected_area) & #Make sure the sublocality matches the one from the selection box
    (df["PRICE"] <= price_limit) & #Make sure the price is within the budget from the slider
    (df["TYPE"].isin(selected_types)) #Make sure the home type is one of the selections in the multibox
]

# [PY1] Function with default value to calculate average sqft
def calculate_price_per_sqft(price, sqft=1):
    return round(price / sqft, 2) if sqft else 0

# [DA9] Add new column using function from above
price_per_sqft_list = [] #Create an empty list to capture data
for i in range(len(specific_filtered_df)): #Loop through the current filtered dataframe
    price = specific_filtered_df.iloc[i]["PRICE"] #Assign price and sqft to variables
    sqft = specific_filtered_df.iloc[i]["PROPERTYSQFT"]
    price_per_sqft_list.append(calculate_price_per_sqft(price, sqft)) #Run the function and append the values to the empty list created above

specific_filtered_df["PRICE_PER_SQFT"] = price_per_sqft_list #Assign the values to a new column in the dataframe

# Sort by price descending
filtered_df = specific_filtered_df.sort_values(by="PRICE", ascending=False)

# Show only important columns
filtered_df = filtered_df[["ADDRESS", "PRICE", "TYPE", "BEDS", "BATH", "PROPERTYSQFT", "PRICE_PER_SQFT"]]

# Show header and results of filtered dataframe
st.markdown(f"**{len(filtered_df)} listings found in {selected_area} under ${price_limit:,}**")
st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)

# [PY4] Using list comprehension to get top 3 best value listings based on price per sqft (see section 2 of document)
best_values_df = filtered_df.sort_values(by="PRICE_PER_SQFT").head(3) #Filter data by lowest price per sqft, only keep the top three values
best_value_listings = [
    f"{row['ADDRESS']} — ${row['PRICE_PER_SQFT']}/sqft" #Loop through the rows in the new values and display the associated address and price per sqft
    for _, row in best_values_df.iterrows()
]
st.markdown(f"**Best Value Listings in {selected_area} (Lowest $/Sqft):**")
for listing in best_value_listings:
    st.write(listing)

tab1, tab2 = st.tabs(["Map View", "Scatter Plot"]) #See section 5 of document

with tab1:
    # [MAP] Interactive map showing locations of filtered listings
    st.subheader("Map of Filtered Listings")

    map_df = specific_filtered_df.dropna(subset=["LATITUDE", "LONGITUDE"])

    if not map_df.empty:
        view = pdk.ViewState(
            latitude=map_df["LATITUDE"].mean(),
            longitude=map_df["LONGITUDE"].mean(),
            zoom=11,
            pitch=0
        )

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_df,
            get_position='[LONGITUDE, LATITUDE]',
            get_radius=100,
            get_color='[200, 30, 0, 160]',
            pickable=True
        )

        tooltip = { #See section 6 of document
            "html": "<b>Address:</b> {ADDRESS}<br><b>Price:</b> ${PRICE}",
            "style": {"backgroundColor": "steelblue", "color": "white"}
        }

        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, tooltip=tooltip))
    else:
        st.write("No listings with location data in this area.")

with tab2:
    # [SEA] Scatter plot: Price vs Square Footage using filtered data (see section 3 of document)
    st.subheader("Price vs. Property Size")
    st.caption("Each dot represents a listing in the selected area, colored by home type.")
    scatter_data = filtered_df.dropna(subset=["PROPERTYSQFT"])  # Remove any items without sqft to avoid confusion
    scatter_data = scatter_data[scatter_data["PROPERTYSQFT"] > 0]  # Also remove items with sqft of 0
    fig, ax = plt.subplots()
    scatter = sea.scatterplot(
        data=scatter_data,
        x="PROPERTYSQFT",
        y="PRICE",
        hue="TYPE",
        palette="muted",
        alpha=0.8
    )
    ax.set_xlabel("Property Size (sqft)")
    ax.set_ylabel("Price ($)")
    ax.set_title("Price vs. Size", fontweight="bold")
    ax.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, _: f"${int(x):,}"))
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.7)
    plt.tight_layout()
    st.pyplot(fig)
    plt.clf()
