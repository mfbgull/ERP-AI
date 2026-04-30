INSERT OR IGNORE INTO warehouses (warehouse_code, warehouse_name, location) 
VALUES ('WH01', 'Main Warehouse', '123 Industrial Ave');

INSERT OR IGNORE INTO users (username, email, full_name, role) 
VALUES 
    ('admin', 'admin@erp.local', 'System Admin', 'admin'),
    ('user', 'user@erp.local', 'Default User', 'user');

INSERT OR IGNORE INTO customers (customer_code, customer_name, contact_name, email, credit_limit, payment_terms_days) 
VALUES 
    ('CUST001', 'ABC Corporation', 'John Smith', 'john@abc.com', 50000, 30),
    ('CUST002', 'XYZ Industries', 'Jane Doe', 'jane@xyz.com', 75000, 45),
    ('CUST003', 'Tech Solutions Ltd', 'Bob Wilson', 'bob@techsol.com', 25000, 30);

INSERT OR REPLACE INTO items (item_code, item_name, description, category, unit_price, cost_price, reorder_level, current_stock) 
VALUES 
    ('PROD001', 'Widget A', 'Standard widget', 'Electronics', 1000, 600, 50, 100),
    ('PROD002', 'Widget B', 'Premium widget', 'Electronics', 1500, 900, 30, 50),
    ('PROD003', 'Gadget X', 'Basic gadget', 'Hardware', 500, 300, 100, 200),
    ('PROD004', 'Gadget Y', 'Advanced gadget', 'Hardware', 800, 480, 50, 75),
    ('PROD005', 'Component Z', 'Essential component', 'Parts', 250, 150, 200, 500);

INSERT OR IGNORE INTO stock_balances (item_id, warehouse_id, quantity)
SELECT id, 1, current_stock FROM items WHERE is_active = 1;

INSERT OR IGNORE INTO settings (setting_key, setting_value) 
VALUES 
    ('default_tax_rate', '0.17'),
    ('default_payment_terms', '30'),
    ('invoice_prefix', 'INV');