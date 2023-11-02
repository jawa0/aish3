import csv
from graphviz import Digraph

def generate_dot_from_data(headers, rows):
    dot = Digraph('KnowledgeGraph', node_attr={'style': 'filled, rounded', 'shape': 'box'})
    
    # Nodes for Product Type
    product_types = set(row[headers.index("Product Type")] for row in rows)
    for product_type in product_types:
        dot.node(product_type, color="lightgreen")
    
    # Nodes and Relationships for each Item
    for row in rows:
        product_type = row[headers.index("Product Type")]
        item_name = row[headers.index("Item Name")]
        catalog_number = row[headers.index("Catalog Number")]
        website = row[headers.index("Website")]
        cost = row[headers.index("Cost")]
        quantity = row[headers.index("Quantity")]
        total = row[headers.index("Total")]
        
        # Node for item
        dot.node(item_name, color="lightblue")
        
        # Relationships from product type to item
        dot.edge(product_type, item_name, label="is a")
        
        # Relationships from item to properties
        dot.edge(item_name, catalog_number, label="has catalog number")
        dot.edge(item_name, website, label="available at")
        dot.edge(item_name, cost, label="has cost")
        dot.edge(item_name, quantity, label="has quantity")
        dot.edge(item_name, total, label="has total cost")

    # Print the DOT representation
    print(dot.source)

# Read CSV Data
data = []
with open('./bio/Dream Lab CAPEX - Sheet1.csv', 'r') as file:
    reader = csv.reader(file)
    for row in reader:
        data.append(row)

# Extract headers and rows
headers = data[0]
rows = data[1:]

generate_dot_from_data(headers, rows)
