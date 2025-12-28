# Kafka Docker Setup Documentation

## Overview

This setup runs Apache Kafka in KRaft mode (without ZooKeeper) along with Kafka UI for monitoring and management. The configuration supports both internal Docker network communication and external host machine access.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Host Machine                          │
│                                                           │
│  ┌──────────────┐                                        │
│  │ producer.py  │──────────────┐                         │
│  │ (Port 9093)  │              │                         │
│  └──────────────┘              │                         │
│                                 ▼                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │           Docker Network (kafka-network)           │  │
│  │                                                     │  │
│  │  ┌──────────────┐           ┌──────────────┐      │  │
│  │  │    Kafka     │◄──────────┤  Kafka UI    │      │  │
│  │  │              │           │              │      │  │
│  │  │ Port 9092 ◄──┼───────────┤ Port 8080    │      │  │
│  │  │ (internal)   │           │              │      │  │
│  │  │              │           └──────────────┘      │  │
│  │  │ Port 9093 ◄──┼─────────────────────────────────┼──┘
│  │  │ (external)   │                                 │
│  │  │              │                                 │
│  │  │ Port 9094    │                                 │
│  │  │ (controller) │                                 │
│  │  └──────────────┘                                 │
│  └────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────┘
```

---

## Port Configuration

| Port | Protocol | Purpose | Used By |
|------|----------|---------|---------|
| 9092 | PLAINTEXT | Internal broker communication | kafka-ui, other Docker containers |
| 9093 | PLAINTEXT_HOST | External host access | producer.py, consumer applications on host |
| 9094 | CONTROLLER | KRaft controller communication | Kafka internal (self-managed) |
| 8080 | HTTP | Kafka UI web interface | Browser access |

---

## Environment Variables Explained

### Kafka Service

#### **KAFKA_KRAFT_MODE**
```yaml
KAFKA_KRAFT_MODE: "true"
```
- **Purpose**: Enables KRaft mode (Kafka Raft metadata mode)
- **Explanation**: KRaft is the new consensus protocol that replaces ZooKeeper for metadata management. This allows Kafka to run without an external ZooKeeper cluster.
- **Value**: `"true"` enables KRaft mode

---

#### **CLUSTER_ID**
```yaml
CLUSTER_ID: "MkU3OEVCNTcwNTJENDM2Qk"
```
- **Purpose**: Unique identifier for the Kafka cluster
- **Explanation**: In KRaft mode, each cluster must have a unique, immutable cluster ID. This is a base64-encoded UUID.
- **Value**: Must be a 22-character base64-encoded string
- **How to generate**: Use `kafka-storage.sh random-uuid` command

---

#### **KAFKA_NODE_ID**
```yaml
KAFKA_NODE_ID: 1
```
- **Purpose**: Unique identifier for this Kafka node
- **Explanation**: In a multi-broker cluster, each broker needs a unique ID. Since we have a single-node cluster, we use ID 1.
- **Value**: Integer (typically starts at 1)

---

#### **KAFKA_PROCESS_ROLES**
```yaml
KAFKA_PROCESS_ROLES: broker,controller
```
- **Purpose**: Defines what roles this Kafka process will perform
- **Explanation**:
  - `broker`: Handles client requests (produce/consume messages)
  - `controller`: Manages cluster metadata and leader elections
  - Combined mode (`broker,controller`): This node acts as both broker and controller (suitable for single-node setups)
- **Other options**: `broker` only, or `controller` only (for dedicated nodes)

---

#### **KAFKA_CONTROLLER_QUORUM_VOTERS**
```yaml
KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9094
```
- **Purpose**: Lists all controller nodes in the KRaft quorum
- **Explanation**: Specifies which nodes participate in metadata consensus
- **Format**: `<node-id>@<hostname>:<port>`
  - `1`: Node ID (matches KAFKA_NODE_ID)
  - `kafka`: Hostname of the controller
  - `9094`: Controller listener port
- **Example for 3 nodes**: `1@kafka1:9094,2@kafka2:9094,3@kafka3:9094`

---

#### **KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR**
```yaml
KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
```
- **Purpose**: Sets replication factor for the internal `__consumer_offsets` topic
- **Explanation**: This topic stores consumer group offsets (position tracking). With a single broker, we can only have a replication factor of 1.
- **Production recommendation**: Set to 3 for fault tolerance
- **Value**: Must be ≤ number of brokers

---

#### **KAFKA_LISTENERS**
```yaml
KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,PLAINTEXT_HOST://0.0.0.0:9093,CONTROLLER://0.0.0.0:9094
```
- **Purpose**: Defines which network interfaces and ports Kafka listens on
- **Explanation**:
  - `PLAINTEXT://0.0.0.0:9092`: Internal Docker network listener
  - `PLAINTEXT_HOST://0.0.0.0:9093`: Host machine listener
  - `CONTROLLER://0.0.0.0:9094`: Controller protocol listener
  - `0.0.0.0`: Listen on all network interfaces
- **Format**: `<protocol>://<interface>:<port>`

---

#### **KAFKA_ADVERTISED_LISTENERS**
```yaml
KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092,PLAINTEXT_HOST://localhost:9093
```
- **Purpose**: Tells clients how to connect to Kafka
- **Explanation**: When clients connect, Kafka sends back these addresses for subsequent connections
  - `PLAINTEXT://kafka:9092`: Address advertised to Docker containers (uses service name `kafka`)
  - `PLAINTEXT_HOST://localhost:9093`: Address advertised to host machine applications
- **Critical**: Must match how clients will actually reach the broker
- **Common issue**: Using `localhost` when clients are in Docker won't work (they'd connect to themselves)

---

#### **KAFKA_LISTENER_SECURITY_PROTOCOL_MAP**
```yaml
KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT,CONTROLLER:PLAINTEXT
```
- **Purpose**: Maps custom listener names to security protocols
- **Explanation**:
  - `PLAINTEXT`: Listener name → `PLAINTEXT`: Security protocol (no encryption)
  - `PLAINTEXT_HOST`: Listener name → `PLAINTEXT`: Security protocol
  - `CONTROLLER`: Listener name → `PLAINTEXT`: Security protocol
- **Available protocols**: `PLAINTEXT`, `SSL`, `SASL_PLAINTEXT`, `SASL_SSL`

---

#### **KAFKA_CONTROLLER_LISTENER_NAMES**
```yaml
KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
```
- **Purpose**: Specifies which listener(s) the controller uses for inter-broker communication
- **Explanation**: The `CONTROLLER` listener (port 9094) is dedicated to KRaft metadata replication and controller operations
- **Value**: Must match one of the listener names defined in KAFKA_LISTENERS

---

#### **KAFKA_LOG_DIRS**
```yaml
KAFKA_LOG_DIRS: /tmp/kafka-combined-logs
```
- **Purpose**: Directory where Kafka stores topic partitions and metadata
- **Explanation**: This is where actual message data is written to disk
- **Value**: File system path inside the container
- **Note**: We also mount a Docker volume to persist this data

---

### Kafka UI Service

#### **KAFKA_CLUSTERS_0_NAME**
```yaml
KAFKA_CLUSTERS_0_NAME: local
```
- **Purpose**: Display name for the cluster in Kafka UI
- **Explanation**: Since Kafka UI can manage multiple clusters, this gives your cluster a friendly name
- **Value**: Any string (used only for display)

---

#### **KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS**
```yaml
KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9092
```
- **Purpose**: Connection string for Kafka UI to connect to Kafka
- **Explanation**:
  - Uses the internal Docker network listener
  - `kafka`: Service name (resolved by Docker DNS)
  - `9092`: Internal broker port
- **Why not localhost**: Kafka UI runs in its own container, so `localhost` would refer to the Kafka UI container, not the Kafka broker

---

## Network Configuration

### kafka-network
```yaml
networks:
  kafka-network:
    driver: bridge
```
- **Purpose**: Creates an isolated network for Kafka services
- **Driver**: `bridge` - Default Docker network driver for container-to-container communication
- **Benefits**:
  - Service discovery via DNS (containers can use service names)
  - Network isolation from other Docker networks
  - Easy inter-container communication

---

## Volume Configuration

### kafka_kraft
```yaml
volumes:
  kafka_kraft:
```
- **Purpose**: Persists Kafka data across container restarts
- **Maps to**: `/var/lib/kafka/data` inside the container
- **Stores**: Topic partitions, consumer offsets, metadata
- **Type**: Named volume (managed by Docker)

---

## How It Works

### 1. **Starting the Services**

When you run `docker-compose up -d`:

1. Docker creates the `kafka-network` bridge network
2. Kafka container starts and:
   - Initializes KRaft metadata storage
   - Starts listening on ports 9092 (internal), 9093 (external), and 9094 (controller)
   - Begins accepting connections
3. Kafka UI container starts and:
   - Connects to Kafka using `kafka:9092`
   - Starts web server on port 8080

---

### 2. **Communication Flow**

#### **From Host Machine (producer.py)**
```
producer.py → localhost:9093 → Kafka container (PLAINTEXT_HOST listener)
```
- Producer connects to `localhost:9093`
- Docker forwards port 9093 to the Kafka container
- Kafka receives the connection on the PLAINTEXT_HOST listener
- Messages are written to topic partitions

#### **From Docker Container (kafka-ui)**
```
kafka-ui → kafka:9092 → Kafka container (PLAINTEXT listener)
```
- Kafka UI connects to `kafka:9092` using Docker's internal DNS
- Connection goes through the kafka-network
- Kafka receives the connection on the PLAINTEXT listener

---

### 3. **Metadata Management (KRaft)**

- Kafka stores cluster metadata (topics, partitions, configs) internally
- No ZooKeeper needed
- Controller role handles:
  - Leader election for partitions
  - Metadata replication
  - Cluster state management
- Uses the CONTROLLER listener (port 9094) for internal communication

---

## Consumer Logic Deep Dive

### Understanding `consumer.poll()`

The Kafka consumer uses a **polling mechanism** to fetch messages from topics. This is fundamentally different from a push model.

#### **The Poll Method**

```python
msg = consumer.poll(timeout)
```

**Parameters:**
- `timeout` (float): Maximum time in seconds to wait for a message
  - `1.0` = wait up to 1 second
  - `0.1` = wait up to 100 milliseconds
  - `0` = non-blocking (return immediately)
  - `None` or omitted = wait indefinitely (NOT recommended)

**Return Value:**
- Returns a `Message` object if a message is available
- Returns `None` if no message arrives within the timeout period
- Check `msg.error()` for any errors

---

### Why the "Interval" Behavior?

When you see your consumer running in "intervals", it's because of the timeout:

```python
while True:
    msg = consumer.poll(1.0)  # <-- This is the key
    if msg is None:
        continue
```

#### **Scenario 1: No Messages Available**

**Timeline:**
```
Time 0.000s: poll(1.0) called
Time 0.000s - 1.000s: Waiting for messages... (sleeps/blocks)
Time 1.000s: Timeout reached, returns None
Time 1.000s: continue statement, loop restarts
Time 1.000s: poll(1.0) called again
Time 1.000s - 2.000s: Waiting for messages...
Time 2.000s: Timeout, returns None
...
```

**What you see:** Appears to run every ~1 second (the "interval")

---

#### **Scenario 2: Messages ARE Available**

**Timeline:**
```
Time 0.000s: poll(1.0) called
Time 0.001s: Message found! Returns immediately
Time 0.001s: Process message
Time 0.001s: Loop continues, poll(1.0) called again
Time 0.002s: Another message found! Returns immediately
Time 0.002s: Process message
...
```

**What you see:** Runs continuously, very fast (thousands per second)

---

### Comparison: With vs Without Consumer

```python
# WITHOUT consumer - tight loop
while True:
    print("1")
# Result: Runs MILLIONS of times per second
# CPU usage: 100%
```

```python
# WITH consumer - blocking poll
while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
# Result: Runs once per second when idle
# CPU usage: ~0%
```

---

### Why Use a Timeout? (Best Practices)

**Without timeout (BAD):**
```python
while True:
    msg = consumer.poll(0)  # Non-blocking
    if msg is None:
        continue
    process(msg)
```

**Problems:**
- 100% CPU usage in tight loop
- Millions of requests per second
- Excessive network traffic
- Battery drain on laptops
- Wastes system resources

**With timeout (GOOD):**
```python
while True:
    msg = consumer.poll(1.0)  # Blocks up to 1 second
    if msg is None:
        continue
    process(msg)
```

**Benefits:**
- CPU-efficient (sleeps when idle)
- Reasonable responsiveness (max 1s latency)
- Reduces broker load
- Industry standard practice

---

### Consumer Configuration Explained

```python
consumer_config = {
    "bootstrap.servers": "localhost:9093",
    "group.id": "order-tracker",
    "auto.offset.reset": "earliest"
}
```

#### **bootstrap.servers**
- **Purpose**: Initial connection point to Kafka cluster
- **Value**:
  - `localhost:9093` for host machine applications
  - `kafka:9092` for Docker containers
- **Multiple brokers**: `"broker1:9093,broker2:9093,broker3:9093"`

---

#### **group.id** (Very Important!)
- **Purpose**: Identifies which consumer group this consumer belongs to
- **How it works**:
  - Consumers in the **same group** share workload (partitions divided among them)
  - Consumers in **different groups** get independent copies of all messages
  - Kafka tracks offset separately for each group

**Example:**

```
Topic: orders (3 partitions)

Group "order-processor":
  Consumer A reads: Partition 0
  Consumer B reads: Partition 1
  Consumer C reads: Partition 2
  → Each message processed once by this group

Group "analytics":
  Consumer D reads: Partitions 0, 1, 2
  → Gets ALL the same messages independently

Group "email-notifier":
  Consumer E reads: Partitions 0, 1, 2
  → Gets ALL the same messages independently
```

**Use Cases:**
- `"order-processor"` - Processes orders for fulfillment
- `"analytics-service"` - Analyzes same orders for metrics
- `"email-notifier"` - Sends email confirmations for same orders

---

#### **auto.offset.reset**
- **Purpose**: Where to start reading when there's no existing offset
- **When it applies**:
  - First time a consumer group subscribes to a topic
  - When committed offset no longer exists (retention expired)

**Values:**

| Value | Behavior | Use Case |
|-------|----------|----------|
| `"earliest"` | Start from beginning of topic | Read all historical data |
| `"latest"` | Start from end (new messages only) | Only care about future messages |
| `"none"` | Throw error if no offset | Strict control, fail fast |

**Example:**
```
Topic has 1000 messages (offsets 0-999)

New consumer with "earliest":
  → Reads from offset 0 (all 1000 messages)

New consumer with "latest":
  → Waits for new messages (starts at offset 1000)
```

---

### Consumer Offset Management

#### **What are Offsets?**

Offsets are like bookmarks tracking which messages each consumer group has processed.

```
Topic: orders, Partition 0

Messages: [0] [1] [2] [3] [4] [5] [6] [7] [8] [9]
                        ↑
                   Last committed offset: 3
                   Next to read: 4
```

#### **Offset Storage**

- Stored in special internal topic: `__consumer_offsets`
- One offset per (consumer group, topic, partition) combination
- Persists across consumer restarts

**Example:**
```
Consumer Group: "order-tracker"
  - orders, partition 0: offset 150
  - orders, partition 1: offset 203
  - orders, partition 2: offset 198

Consumer Group: "analytics"
  - orders, partition 0: offset 50   (independent!)
  - orders, partition 1: offset 62
  - orders, partition 2: offset 47
```

---

#### **Automatic vs Manual Commit**

**Automatic Commit (Default):**
```python
consumer_config = {
    "enable.auto.commit": True,        # Default
    "auto.commit.interval.ms": 5000    # Every 5 seconds
}

# Offsets committed automatically in background
while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    process(msg)  # If this crashes, might reprocess messages
```

**Pros:** Simple, less code
**Cons:** Can lose or duplicate messages on crashes

---

**Manual Commit (Recommended for Critical Apps):**
```python
consumer_config = {
    "enable.auto.commit": False
}

while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue

    process(msg)          # Process message
    consumer.commit()     # THEN commit offset
```

**Pros:** Exact control, no message loss
**Cons:** Slightly more code

---

### Consumer Groups and Partition Assignment

#### **Single Consumer**
```
Topic: orders (3 partitions)

Partition 0 ────┐
Partition 1 ────┼──→ Consumer A (group: "tracker")
Partition 2 ────┘

All partitions assigned to one consumer
```

---

#### **Multiple Consumers (Same Group) - Load Balancing**
```
Topic: orders (3 partitions)

Partition 0 ────→ Consumer A ┐
Partition 1 ────→ Consumer B ├─ group: "tracker"
Partition 2 ────→ Consumer C ┘

Workload distributed: each partition → one consumer
```

---

#### **More Consumers than Partitions**
```
Topic: orders (3 partitions)

Partition 0 ────→ Consumer A ┐
Partition 1 ────→ Consumer B ├─ group: "tracker"
Partition 2 ────→ Consumer C │
                  Consumer D ─┘ (idle, no assignment)
                  Consumer E ─┘ (idle, no assignment)

Extra consumers sit idle (waste of resources)
```

**Recommendation:** Number of consumers ≤ number of partitions

---

#### **Multiple Consumer Groups - Independent Processing**
```
Topic: orders (3 partitions)

          ┌──→ Consumer A (group: "processor")    → Processes orders
Messages ─┼──→ Consumer B (group: "analytics")    → Analyzes orders
          └──→ Consumer C (group: "notifications") → Sends emails

Each group gets ALL messages independently
```

---

### Complete Consumer Example

```python
import json
from confluent_kafka import Consumer, KafkaError

# Configuration
consumer_config = {
    "bootstrap.servers": "localhost:9093",
    "group.id": "order-tracker",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,  # Manual commit for reliability
}

# Create consumer
consumer = Consumer(consumer_config)
consumer.subscribe(['orders'])

print("🟢 Consumer started and subscribed to 'orders' topic")

try:
    while True:
        # Poll with 1 second timeout
        msg = consumer.poll(1.0)

        # No message within timeout
        if msg is None:
            continue

        # Check for errors
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                # End of partition - not an error
                continue
            else:
                print(f"❌ Error: {msg.error()}")
                continue

        # Process message
        try:
            value = msg.value().decode('utf-8')
            order = json.loads(value)
            print(f"📦 Received order: {order}")

            # Simulate processing
            # ... business logic here ...

            # Commit offset after successful processing
            consumer.commit()

        except json.JSONDecodeError as e:
            print(f"⚠️  Invalid JSON: {e}")
            # Commit to skip bad message
            consumer.commit()

        except Exception as e:
            print(f"❌ Processing error: {e}")
            # Don't commit - will retry on restart

except KeyboardInterrupt:
    print("\n🔴 Consumer shutting down...")

finally:
    consumer.close()
    print("✅ Consumer closed")
```

---

### Performance Tuning

#### **Adjust Poll Timeout**

```python
# Fast response, higher CPU when idle
msg = consumer.poll(0.1)  # 100ms

# Balanced (recommended default)
msg = consumer.poll(1.0)  # 1 second

# Slower response, lowest CPU
msg = consumer.poll(5.0)  # 5 seconds
```

---

#### **Batch Processing**

```python
batch = []
batch_size = 100

while True:
    msg = consumer.poll(0.1)

    if msg is not None and not msg.error():
        batch.append(msg)

    # Process when batch full or timeout
    if len(batch) >= batch_size or (msg is None and batch):
        process_batch(batch)  # Process 100 at once
        consumer.commit()
        batch = []
```

---

#### **Fetch Configuration**

```python
consumer_config = {
    "fetch.min.bytes": 1024,           # Min data per request (1KB)
    "fetch.max.wait.ms": 500,          # Max wait for min bytes
    "max.partition.fetch.bytes": 1048576,  # Max per partition (1MB)
}
```

---

## Testing the Setup

### 1. Check Kafka is Running
```bash
docker logs kafka
```

### 2. Access Kafka UI
Open browser: http://localhost:8080

### 3. Run Producer
```bash
python producer.py
```

### 4. Run Consumer
```bash
python consumer.py
```

### 5. Create a Topic Manually
```bash
docker exec -it kafka kafka-topics --create \
  --topic test-topic \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1
```

### 6. List Topics
```bash
docker exec -it kafka kafka-topics --list \
  --bootstrap-server localhost:9092
```

### 7. Check Consumer Group Status
```bash
# List all consumer groups
docker exec -it kafka kafka-consumer-groups --list \
  --bootstrap-server localhost:9092

# Describe specific group
docker exec -it kafka kafka-consumer-groups --describe \
  --group order-tracker \
  --bootstrap-server localhost:9092
```

---

## Troubleshooting

### Issue: "Connection to node 1 could not be established"

**Cause**: Mismatch between advertised listeners and actual connectivity

**Solution**:
- Ensure `KAFKA_ADVERTISED_LISTENERS` matches how clients connect
- For Docker containers: use service name (`kafka:9092`)
- For host machine: use `localhost:9093`

---

### Issue: Producer can't connect from host

**Cause**: Using wrong port or advertised listener not configured

**Solution**:
- Use `localhost:9093` in producer configuration
- Ensure port 9093 is exposed in docker-compose.yml
- Verify PLAINTEXT_HOST listener is configured

---

### Issue: Kafka UI shows cluster offline

**Cause**: Kafka UI can't resolve or connect to Kafka

**Solution**:
- Ensure both services are on the same network
- Use service name (`kafka`) not `localhost` in Kafka UI config
- Check Kafka is actually running: `docker ps`

---

## Production Recommendations

### For Production Environments:

1. **Replication**
   - Set `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3`
   - Run at least 3 Kafka brokers

2. **Security**
   - Use SSL/TLS listeners instead of PLAINTEXT
   - Enable SASL authentication
   - Configure ACLs for authorization

3. **Resources**
   - Allocate sufficient memory (at least 4GB per broker)
   - Use dedicated storage volumes with good I/O
   - Monitor disk space (Kafka is disk-intensive)

4. **Networking**
   - Use separate listeners for internal/external traffic
   - Configure firewalls appropriately
   - Consider using load balancers

5. **Monitoring**
   - Set up JMX metrics export
   - Use monitoring tools (Prometheus, Grafana)
   - Configure alerting for critical metrics

---

## References

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [KRaft Mode Overview](https://kafka.apache.org/documentation/#kraft)
- [Kafka UI GitHub](https://github.com/provectus/kafka-ui)
- [Confluent Platform Docker Images](https://docs.confluent.io/platform/current/installation/docker/image-reference.html)

---

## Quick Commands Reference

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f kafka
docker-compose logs -f kafka-ui

# Restart services
docker-compose restart

# Remove everything (including volumes)
docker-compose down -v

# Access Kafka container shell
docker exec -it kafka bash

# Create topic
docker exec -it kafka kafka-topics --create \
  --topic my-topic \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1

# Describe topic
docker exec -it kafka kafka-topics --describe \
  --topic my-topic \
  --bootstrap-server localhost:9092

# List consumer groups
docker exec -it kafka kafka-consumer-groups --list \
  --bootstrap-server localhost:9092

# Console producer (for testing)
docker exec -it kafka kafka-console-producer \
  --topic my-topic \
  --bootstrap-server localhost:9092

# Console consumer (for testing)
docker exec -it kafka kafka-console-consumer \
  --topic my-topic \
  --bootstrap-server localhost:9092 \
  --from-beginning
```
