# try_fastapi_sqlalchemy_strawberry

## 起動

```
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 確認

### REST API

ブラウザで http://127.0.0.1:8000/docs にアクセスし、Swagger UIを使って各エンドポイント（POST /items/, GET /items/, GET /items/{id}, DELETE /items/{id} など）を確認できる

### GraphQL API

ブラウザで http://127.0.0.1:8000/graphql にアクセスする。Strawberryが提供するGraphiQL（または設定によってはApollo Sandboxなど）インターフェースが表示される。
ここでGraphQLクエリやミューテーションを実行してテストできる。

```
# 全アイテム取得
query GetItems {
  items {
    id
    name
    price
    description
  }
}
```

```
# 特定アイテム取得
query GetSingleItem {
   item(itemId: 1) {
      id
      name
   }
}
```


```
# 新規アイテム追加
mutation AddNewItem {
  addItem(item: {name: "GraphQL Item", price: 123.45, description: "Added via GraphQL"}) {
    id
    name
    price
  }
}
```


```
# アイテム削除
mutation DeleteSpecificItem {
   deleteItem(itemId: 1)
}```


