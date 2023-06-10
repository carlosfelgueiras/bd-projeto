import random

sku_list = ["TS123456","KS944RUR","KS93528TUT","KA17120203","HM21KMPW","X00299X9JF"]
sku_preface = "TEST"
product_description = "Test description."
n_entries = 3000
A_percentage = 0

for product_no in range(6,n_entries):
    sku_number=random.randint(1,999999999)
    sku=sku_preface+str(sku_number)
    A_percentage = random.randint(0,100)
    if(product_no <= 20):
        name= "A"+str(product_no)
    else:
        name= "B"+str(product_no)
    price=random.random()+random.randint(0,100)
    print("INSERT INTO product VALUES('{}', '{}', '{}', {});".format(sku,name,product_description,price))

for order_no in range(24,n_entries):
    customer_no=random.randint(1,3)
    day=random.randint(1,27)
    month=random.randint(1,12)
    year=random.randint(2022,2023)
    print("INSERT INTO orders VALUES({}, {}, '{}-{}-{}');".format(order_no,customer_no,year,month,day))

for order_no in range(24,n_entries):
    product_sku=random.choice(sku_list)
    qty=random.randint(1,50)
    print("INSERT INTO contains VALUES({}, '{}', {});".format(order_no,product_sku,qty))