-- Create a new table
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    start_date DATE
);

-- Insert some data
INSERT INTO employees (name, role, start_date) VALUES ('Alice', 'Developer', '2023-01-15');
INSERT INTO employees (name, role, start_date) VALUES ('Bob', 'Designer', '2022-11-20');
INSERT INTO employees (name, role, start_date) VALUES ('Charlie', 'Manager', '2021-05-10');
