# defining a closure such that this function remembers the apply_discount function protected..
def discount_calculator(percent):

    def apply_discount(price):
       return  price  - (percent/100) * price
    
    return apply_discount
