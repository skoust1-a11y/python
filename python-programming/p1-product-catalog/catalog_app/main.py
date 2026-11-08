from .products import add_product,add_products  #relative imports
from .filters  import filter_map_list,filter_list #relative imports

def main():
    my_products = add_products(
        add_product('Monitor',12000,'Electronics'),
        add_product('Laptop',550000,'Electronics',stock = 6),
        add_product('Mouse',800,'Electronics',stock = 2),
        add_product('Shoes',2500,'Fashion',stock = 3),
        add_product('Keyboard',1500,'Electronics',stock = 10),
        add_product('Headphones',3500,'Electronics',stock = 5),
        add_product('Smartphone',45000,'Electronics',stock = 4),
        add_product('Tablet',30000,'Electronics',stock = 3),
        add_product('Backpack',1800,'Accessories',stock = 7),
        add_product('Watch',12000,'Accessories',stock = 6),
        add_product('WaterBottle',500,'Home',stock = 20),
        add_product('Chair',4500,'Furniture',stock = 8),
        add_product('Desk',9000,'Furniture',stock = 2),
        add_product('Fan',2500,'Home Appliances',stock = 5)    
        ) # adding and storing a list of dictionaries using the helper functions add_product to store single product and add_products to store list of products
    

    # print(my_products)
    print('All Products:')
    for x in my_products:
            print(f'- {x['name']}: ₹{x['price']} ({x['category']}, Stock: {x.get('stock','N/A')})')
    print()

    print('In-stock Products above ₹2000:') # filtering products whose price is above 2000 and printing them
    for x in filter_list(my_products):
         print(f'- {x['name']}: ₹{x['price']} ({x['category']}, Stock: {x.get('stock')})')

    
    print()
    print('After Applying Festival Discount (20%):') # printing the products with their discount from list of dictionaries
    for x in filter_map_list(my_products):
         print(f'- {x['name']}: ₹{x['price']} ({x['category']}, Stock: {x.get('stock')})')
         

    
if __name__ == "__main__":
    main()


