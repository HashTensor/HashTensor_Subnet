# HashTensor Miner Registration Guide

> **Note:** For subnet registration and system overview, see the [main README](../README.md).

---

## 🚀 Quick Overview

1. **Start your ASIC/GPU Kaspa miner using the following pool and wallet:**

   - **Pool:** `pool.hashtensor.com:5555`
   - **Wallet address (pool owner):**
     - For **mainnet (Finney)**:  
       `kaspa:qr4ksh6s3rmy5f4qyql2kh7p9z7f4c55da5r5gz2nnsd8ctt4k69whtr4u0wp`
     - For **testnet**:  
       `kaspa:qq7yl7tjhkyr56x380j7hpa2r4jz97dyqn74a69wumpe5rv97wyxk4cxa7e7t`
   - **Worker name:** *Must contain your Bittensor hotkey for security validation.*

   > **Note:**
   > If you use a different Kaspa wallet for mining (not the pool owner wallet above), you can still mine Kaspa in our pool and increase your hashrate, but you will **not** be able to register your worker in the subnet or receive Alpha token rewards in Bittensor.

2. **Bind your hotkey to your worker using the binding script:**

   > **🟢 Recommended:** Create and activate a Python virtual environment (venv) before running the script. This helps keep dependencies isolated and your system Python clean.
   >
   > ```bash
   > python3 -m venv hashtensor-venv
   > source hashtensor-venv/bin/activate
   > ```
   >
   > You can deactivate the venv later with `deactivate`. This step is optional but recommended.

   ```bash
   curl -s https://raw.githubusercontent.com/HashTensor/HashTensor_Subnet/main/scripts/bind_worker.py | python3 - \
     --worker YOUR_WORKER_NAME \
     --wallet.name my_wallet \
     --wallet.hotkey my_hotkey \
     --subtensor.network finney
   ```

   > **ℹ️ Note:** The script requires Python and the following packages: `bittensor-wallet`, `async-substrate-interface`, `scalecodec`, `aiohttp`.  
   > If any are missing, the script will tell you how to install them.

---

## 📋 Detailed Instructions

### 1. Prerequisites

- **A registered Bittensor hotkey** in the HashTensor subnet (see [main README](../README.md)).
- **A Kaspa mining worker** with a unique, private name.
- **Your Bittensor wallet** (wallet name and hotkey).

---

### 2. Worker Name Security Requirements

**🔒 IMPORTANT:** Your worker name **must contain your Bittensor hotkey** for security validation. This prevents unauthorized registration of workers.

**Valid worker name examples:**
- `5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty` (hotkey as worker name)
- `my_worker_5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty` (hotkey at the end)
- `5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty_worker1` (hotkey at the beginning)
- `worker_5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty_01` (hotkey in the middle)

**Invalid worker name examples:**
- `worker1` (doesn't contain hotkey)
- `my_miner` (doesn't contain hotkey)
- `kaspa_worker` (doesn't contain hotkey)

> **💡 Tip:** You can find your hotkey by running: `btcli wallet overview --wallet.name <your_wallet_name>`

---

### 3. GPU Mining: Step-by-Step (lolMiner Example)

Follow these steps to start mining Kaspa with your GPU using **lolMiner**:

```bash
# 1. Download lolMiner
wget -O lolMiner_v1.76_Lin64.tar.gz \
  https://github.com/Lolliedieb/lolMiner-releases/releases/download/1.76/lolMiner_v1.76_Lin64.tar.gz

# 2. Extract it
tar -xzf lolMiner_v1.76_Lin64.tar.gz

# 3. Enter the directory
cd 1.76

# 4. Run the miner (replace WALLET and WORKER_NAME with your own)
./lolMiner --algo KASPA \
  --user kaspa:qr4ksh6s3rmy5f4qyql2kh7p9z7f4c55da5r5gz2nnsd8ctt4k69whtr4u0wp.YOUR_WORKER_NAME \
  --pool pool.hashtensor.com:5555
```

- **Replace** `kaspa:qr4ksh6s3rmy5f4qyql2kh7p9z7f4c55da5r5gz2nnsd8ctt4k69whtr4u0wp` with your Kaspa wallet address if you want to mine to your own wallet, or use the pool owner address as shown above.
- **Replace** `YOUR_WORKER_NAME` with your unique worker name that contains your hotkey.
- **Pool address:** `pool.hashtensor.com:5555`.

---

### 4. Important Security Steps

#### **Before Registration**

- Generate a unique worker name for your Kaspa miner that **contains your Bittensor hotkey**.
- **Keep this name private** until registration is complete.
- If the name is compromised, restart your miner with a new name.

#### **During Registration**

- **Start your miner first** with your chosen worker name.
- **Immediately run the registration script** to bind your hotkey to your worker:

  ```bash
  curl -s https://raw.githubusercontent.com/HashTensor/HashTensor_Subnet/main/scripts/bind_worker.py | python3 - \
    --worker YOUR_WORKER_NAME \
    --wallet.name <wallet_name> \
    --wallet.hotkey <hotkey_name> \
    --subtensor.network finney
  ```

- Complete registration **before sharing your worker name publicly**.

#### **After Registration**

- Your worker name is now securely linked to your hotkey.
- You can now share your worker name publicly.
- The subnet will track your mining contributions.

---

### 5. Multiple Workers Support

- You can register multiple workers under the same hotkey.
- Each worker must have a unique name that contains your hotkey.
- Your total mining capacity is the sum of all your registered workers.
- Register each worker separately using the same hotkey.

**Example:**

```bash
# Register first worker
curl -s https://raw.githubusercontent.com/HashTensor/HashTensor_Subnet/main/scripts/bind_worker.py | python3 - \
  --worker 5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty_worker1 \
  --wallet.name my_wallet \
  --wallet.hotkey my_hotkey \
  --subtensor.network finney

# Register second worker
curl -s https://raw.githubusercontent.com/HashTensor/HashTensor_Subnet/main/scripts/bind_worker.py | python3 - \
  --worker 5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty_worker2 \
  --wallet.name my_wallet \
  --wallet.hotkey my_hotkey \
  --subtensor.network finney
```

---

### 6. Unbinding Workers

When you need to remove a worker from the subnet (e.g., when decommissioning hardware or changing worker names), you can use the unbind scripts.

#### **Unbind a Single Worker**

To unbind a specific worker from your hotkey:

```bash
curl -s https://raw.githubusercontent.com/HashTensor/HashTensor_Subnet/main/scripts/unbind_worker.py | python3 - \
  --worker YOUR_WORKER_NAME \
  --wallet.name my_wallet \
  --wallet.hotkey my_hotkey \
  --subtensor.network finney
```

**Example:**
```bash
curl -s https://raw.githubusercontent.com/HashTensor/HashTensor_Subnet/main/scripts/unbind_worker.py | python3 - \
  --worker 5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty_worker1 \
  --wallet.name my_wallet \
  --wallet.hotkey my_hotkey \
  --subtensor.network finney
```

#### **Unbind All Workers for a Hotkey**

To unbind all workers associated with your hotkey at once:

```bash
curl -s https://raw.githubusercontent.com/HashTensor/HashTensor_Subnet/main/scripts/unbind_all.py | python3 - \
  --wallet.name my_wallet \
  --wallet.hotkey my_hotkey \
  --subtensor.network finney
```

**⚠️ Important Notes:**
- The `unbind_all` script will discover all workers registered to your hotkey across all validators
- It will show you the list of workers before proceeding
- **You must confirm with "yes"** to proceed with the unbinding
- This action cannot be undone - workers will need to be re-registered if you want to use them again

**Making it Interactive with curl:**

The script now tries to handle interactive input even when piped via curl. If the standard approach doesn't work, try these alternatives:

**Option 1: Use /dev/tty (Recommended)**
```bash
curl -s https://raw.githubusercontent.com/HashTensor/HashTensor_Subnet/main/scripts/unbind_all.py | python3 - \
  --wallet.name my_wallet \
  --wallet.hotkey my_hotkey \
  --subtensor.network finney
```
The script will automatically try to use `/dev/tty` for interactive input if stdin is redirected.

**Option 2: Download and Run Locally**
```bash
# Download the script
curl -s https://raw.githubusercontent.com/HashTensor/HashTensor_Subnet/main/scripts/unbind_all.py > unbind_all.py

# Run it directly
python3 unbind_all.py \
  --wallet.name my_wallet \
  --wallet.hotkey my_hotkey \
  --subtensor.network finney
```

**For Automated/Non-Interactive Use:**
If you're using the script in a non-interactive environment (like when piping via curl), add the `--confirm` flag to skip the confirmation prompt:

```bash
curl -s https://raw.githubusercontent.com/HashTensor/HashTensor_Subnet/main/scripts/unbind_all.py | python3 - \
  --wallet.name my_wallet \
  --wallet.hotkey my_hotkey \
  --subtensor.network finney \
  --confirm
```

**Example Output:**
```
Wallet hotkey: 5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty
Network: finney
Found 15 validators

Fetching mappings from validators...
Found 2 workers in validator 5ABC...: ['worker1', 'worker2']
Found 1 workers in validator 5DEF...: ['worker3']

Total unique workers to unbind: 3
Workers: ['worker1', 'worker2', 'worker3']

Do you want to unbind all 3 workers? (yes/no): yes

Unbinding 3 workers...

Unbinding worker: worker1
Validator 5ABC... unbind response: {"message":"Worker unbound successfully"}
Validator 5DEF... unbind response: {"message":"Worker unbound successfully"}
...

Unbind process completed for 3 workers
```

#### **When to Use Unbind Scripts**

- **Single worker unbind:** When decommissioning a specific mining rig or changing a worker's name
- **Unbind all:** When switching to a new hotkey, decommissioning all mining operations, or troubleshooting registration issues

---

### 7. Common Issues

#### ⚠️ Miner Startup Errors

- **"Worker not authorized" or similar unauthorized error:**  
  This means the worker name is already taken by another user. You must choose a different, unique worker name and restart your miner with the new name.

#### ⚡ Validator Response Errors

- **"Worker not found":**  
  Make sure your worker is running and the name is correct.
- **"Worker name must contain the hotkey for security validation":**  
  Your worker name must include your Bittensor hotkey. Check the worker name format requirements above.
- **"Hotkey not registered":**  
  Register your hotkey in the subnet first (see [main README](../README.md)).
- **"Registration time is too far from current UTC time":**  
  Try running the script again.
- **"Invalid signature":**  
  Check your wallet credentials.

#### 🔗 Unbind Errors

- **"Worker not found for this hotkey":**  
  The worker is not registered to your hotkey, or it was already unbound.
- **"Worker already unbound":**  
  The worker has already been unbound from your hotkey.

---

### 8. Security Tips

- Never share your worker name **before registration**.
- If your worker name is compromised, stop mining and restart with a new name.
- Use unique worker names for each mining instance.
- **Always include your hotkey in the worker name** for security validation.
- Register immediately after starting your miner.
- **Be careful with unbind_all** - it will remove all workers for your hotkey and requires re-registration.

---

### 9. Script Requirements

> The registration and unbind scripts require:
> - Python 3.12+
> - The following Python packages:  
>   `bittensor-wallet`, `async-substrate-interface`, `scalecodec`, `aiohttp`
>
> If you run the script and a package is missing, it will print a message like:
> ```
> Error: Missing required packages. Please install them using pip:
> pip install bittensor-wallet async-substrate-interface scalecodec aiohttp
> ```

---

**🎉 You are now ready to register your Kaspa miner with HashTensor!**  
If you have any issues, check the error messages or ask for help in the community.
