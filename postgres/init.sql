-- Sample password for local development only
CREATE USER racetrack WITH ENCRYPTED PASSWORD 'dev-25ZjbUDJH6MzmUR';
GRANT ALL PRIVILEGES ON DATABASE lifecycle_db TO racetrack;
