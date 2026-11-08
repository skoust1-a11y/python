from .discounts import discount_calculator


#using aggregation functions using lambda functions to simplify the process

def filter_map_list(raw_list : list) -> list:
    filtered_list_based_on_price = list(filter(
        lambda x : x['price'] > 2000 and x.get('stock',0) > 0,raw_list))
    
    filtered_list_based_on_category = list(filter(
        lambda x : x['category'] =='Fashion',raw_list))
    
    discount = discount_calculator(20)

    final_filteerd_discounted_price = list(map(
        lambda x : {**x,
                    'price':
                    discount(x['price']) },filtered_list_based_on_price))
    
    # print(final_filteerd_discounted_price)
    
    return final_filteerd_discounted_price

def filter_list(raw_list : list) -> list:
    filtered_list_based_on_price = list(filter(
        lambda x : x['price'] > 2000 and x.get('stock',0) > 0,raw_list))
    
    # filtered_list_based_on_category = list(filter(
    #     lambda x : x['category'] =='Fashion',raw_list))
    
    # print(final_filteerd_discounted_price)
    
    return filtered_list_based_on_price
