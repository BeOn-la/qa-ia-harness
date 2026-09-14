CREATE TABLE dbo.[{table}] (
    Id int NOT NULL PRIMARY KEY,
    Url nvarchar(200) NULL
);
INSERT INTO dbo.[{table}] (Id, Url) VALUES
    (1, NULL), (2, N'-'), (3, N' - '), (4, N''), (5, N'https://example.invalid/item');
