INSERT INTO supplier (tin,name,address,sku,date) VALUES
('SUPL123123', 'Monster', 'Rua de S.Roque nº39, Lisboa, Portugal', 'MW123123', '2024-01-22'),
('SUPL123124', 'RedBull', 'Rua de S.João nº32, Lisboa, Portugal', 'AB12345', '2024-02-22'),
('SUPL123125', 'Coca-Cola', 'Rua do Técnico nº12, Lisboa, Portugal', 'CC109231', '2024-03-23');

INSERT INTO customer (cust_no,name,email,phone,address) VALUES
(1, 'Jorge Mendes', 'jorgemendes@gmail.com', '919212354', 'Rua de S.Roque nº3, Lisboa, Portugal'),
(2, 'Miguel Venâncio', 'miguelvenancio@gmail.com', '919098765', 'Rua de S. Sebastião nº9, Porto, Portugal'),
(3, 'Camila Pereira', 'camilapereira@gmail.com', '919827632', 'Rua do Carvalhal nº8, Coimbra, Portugal');

INSERT INTO orders (order_no,cust_no,date) VALUES
(1, 1, '2024-04-23'),
(2, 2, '2024-05-23'),
(3, 3, '2024-06-23');

INSERT INTO contains(order_no, SKU, qty) VALUES
(1, 'AB12345', 3),
(2, 'CC109231', 4),
(3, 'MW123123', 5);
