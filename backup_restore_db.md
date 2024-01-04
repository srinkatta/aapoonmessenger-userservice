# PostgreSQL Database Export and Import Guide

This guide provides step-by-step instructions on exporting and importing a PostgreSQL database, including the process of changing the schema namespace during import.

## Exporting PostgreSQL Database

### Command:

```bash
pg_dump -h <source_host> -U <source_username> -d <source_database> -f <output_file>
```

### Example:

```bash
pg_dump -h localhost -U root -d postgres -f circle.sql
```

#### Parameters:
- `-h` or `--host`: Specifies the host name of the PostgreSQL server.
- `-U` or `--username`: Specifies the username to connect to the PostgreSQL server.
- `-d` or `--dbname`: Specifies the name of the database to be exported.
- `-f` or `--file`: Specifies the output file where the SQL dump will be saved.

## Modifying the SQL Dump

After generating the SQL dump file (e.g., `circle.sql`), open it using a text editor and replace the default namespace `public.` with your custom schema name.

For example, replace all occurrences of `public.` with `<custom_schema_name>.` in the SQL dump file.

Because by default any database which is created in postgres have `public` schema. And whenever we export the database
we get the tables in the format of `namespace.tablename` e.g. `public.user_user` etc.
So, we need to change it ourselves before the actual import so we can change the default schema as per our need and send
data to respective schema which we want it to go.

## Importing PostgreSQL Database

### Command:

```bash
psql -h <target_host> -U <target_username> -d <target_database> -f <input_file>
```

### Example:

```bash
psql -h user-service-qa-cluster-instance-1.ckqgz6u3jrul.us-east-1.rds.amazonaws.com -U postgres -d microservices -f circle.sql
```

#### Parameters:
- `-h` or `--host`: Specifies the host name of the target PostgreSQL server.
- `-U` or `--username`: Specifies the username to connect to the target PostgreSQL server.
- `-d` or `--dbname`: Specifies the name of the target database for import.
- `-f` or `--file`: Specifies the input file containing the SQL dump to be imported.

## Important Notes:
- Ensure that you have the necessary permissions to perform database export and import operations.
- Replace `<source_host>`, `<source_username>`, `<source_database>`, `<output_file>`, `<target_host>`, `<target_username>`, `<target_database>`, and `<input_file>` with your specific values.
- Customize `<custom_schema_name>` to the desired schema name during the import process.

By following these steps, you can successfully export a PostgreSQL database, modify the schema namespace, and import it into another PostgreSQL database.
