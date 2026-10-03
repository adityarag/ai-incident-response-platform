# API Documentation

## Services Architecture

The AI Incident Response Platform consists of the following microservices:

1. **API Gateway** (`:8000`) - Entry point, reverse proxy, request correlation tracing.
2. **Order Service** (`:8001`) - Order lifecycle management and downstream payment coordination.
3. **Payment Service** (`:8002`) - Transaction processing, idempotency support, and ledger.
4. **PostgreSQL** (`:5432`) - Central datastore for services, incidents, orders, payments, and audit logs.

---

## 1. API Gateway (`:8000`)

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Gateway liveness and database connection status |
| `GET` | `/ready` | Gateway readiness probe |
| `POST` | `/api/v1/orders` | Proxies order creation to Order Service |
| `GET` | `/api/v1/orders/{order_id}` | Proxies order lookup |
| `GET` | `/api/v1/orders` | Proxies order list with pagination |
| `GET` | `/api/v1/payments/{payment_id}` | Proxies payment verification |

All requests accept and forward `X-Correlation-ID` header. If absent, a unique UUID is generated and appended to responses.

---

## 2. Order Service (`:8001`)

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health status |
| `GET` | `/ready` | Service readiness probe |
| `POST` | `/orders` | Creates an order record and invokes Payment Service |
| `GET` | `/orders/{order_id}` | Fetch order details |
| `GET` | `/orders` | Query orders (`skip`, `limit`) |

#### Create Order Payload
```json
{
  "customer_id": "CUST-100",
  "item": "Cloud Server Instance",
  "quantity": 1,
  "amount": 49.99,
  "currency": "USD"
}
```

---

## 3. Payment Service (`:8002`)

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health status |
| `GET` | `/ready` | Service readiness probe |
| `POST` | `/payments/process` | Processes transaction with idempotency support |
| `GET` | `/payments/{payment_id}` | Query payment status |

#### Process Payment Payload
```json
{
  "order_id": "ORD-1234",
  "customer_id": "CUST-100",
  "amount": 49.99,
  "currency": "USD",
  "idempotency_key": "idemp-ORD-1234"
}
```
