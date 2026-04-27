def add_product(name,price,category,**kwargs) -> dict:
    my_dict = {}
    def add_prod(d,key,value):
        d[key]=value
    add_prod(my_dict,'name',name)
    add_prod(my_dict,'price',price)
    add_prod(my_dict,'category',category)

    for key,value in kwargs.items():
        my_dict[key] = value
    
    return my_dict
    
def add_products(*args) -> list:
    my_prod_list = [x for x in args]
    return my_prod_list