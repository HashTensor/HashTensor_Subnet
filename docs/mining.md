# HashTensor Miner Registration Guide

---

## 🚀 Quick Overview

1. **Register your hotkey in the subnet:**

   - For the **Finney network** (mainnet):
     ```bash
     btcli subnet register --netuid 16
     ```
   - For the **testnet**:
     ```bash
     btcli subnet register --netuid 368
     ```

2. **Start your ASIC/GPU Kaspa miner using the following pool and wallet:**

   - **Pool:** `pool.hashtensor.com:5555`
   - **Wallet address (pool owner):**  
     `kaspa:qr4ksh6s3rmy5f4qyql2kh7p9z7f4c55da5r5gz2nnsd8ctt4k69whtr4u0wp`
   - **Worker name:** *Choose a unique name for your worker.*

   > **Note:**
   > If you use a different Kaspa wallet for mining (not the pool owner wallet above), you can still mine Kaspa in our pool and increase your hashrate, but you will **not** be able to register your worker in the subnet or receive Alpha token rewards in Bittensor.

3. **Bind your hotkey to your worker using the registration script:**

   > **🟢 Recommended:** Create and activate a Python virtual environment (venv) before running the script. This helps keep dependencies isolated and your system Python clean.
   >
   > ```bash
   > python3 -m venv hashtensor-venv
   > source hashtensor-venv/bin/activate
   > ```
   >
   > You can deactivate the venv later with `deactivate`. This step is optional but recommended.

   ```bash
   curl -s https://raw.githubusercontent.com/HashTensor/HashTensor_Subnet/develop/scripts/register_miner.py | python3 - \
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

- **A registered Bittensor hotkey** in the HashTensor subnet (use `btcli subnet register`).
- **A Kaspa mining worker** with a unique, private name.
- **Your Bittensor wallet** (wallet name and hotkey).

---

### 2. GPU Mining: Step-by-Step (lolMiner Example)

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
- **Replace** `YOUR_WORKER_NAME` with your unique worker name.
- **Pool address:** `pool.hashtensor.com:5555`.

---

### 3. Important Security Steps

#### **Before Registration**

- Generate a unique worker name for your Kaspa miner.
- **Keep this name private** until registration is complete.
- If the name is compromised, restart your miner with a new name.

#### **During Registration**

- **Start your miner first** with your chosen worker name.
- **Immediately run the registration script** to bind your hotkey to your worker:

  ```bash
  curl -s https://raw.githubusercontent.com/HashTensor/HashTensor_Subnet/develop/scripts/register_miner.py | python3 - \
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

### 4. Multiple Workers Support

- You can register multiple workers under the same hotkey.
- Each worker must have a unique name.
- Your total mining capacity is the sum of all your registered workers.
- Register each worker separately using the same hotkey.

**Example:**

```bash
# Register first worker
curl -s https://raw.githubusercontent.com/HashTensor/HashTensor_Subnet/develop/scripts/register_miner.py | python3 - \
  --worker worker1 \
  --wallet.name my_wallet \
  --wallet.hotkey my_hotkey \
  --subtensor.network finney

# Register second worker
curl -s https://raw.githubusercontent.com/HashTensor/HashTensor_Subnet/develop/scripts/register_miner.py | python3 - \
  --worker worker2 \
  --wallet.name my_wallet \
  --wallet.hotkey my_hotkey \
  --subtensor.network finney
```

---

### 5. Common Issues

#### ⚠️ Miner Startup Errors

- **"Worker not authorized" or similar unauthorized error:**  
  This means the worker name is already taken by another user. You must choose a different, unique worker name and restart your miner with the new name.

#### ⚡ Validator Response Errors

- **"Worker not found":**  
  Make sure your worker is running and the name is correct.
- **"Hotkey not registered":**  
  Register your hotkey in the subnet first using `btcli subnet register`.
- **"Registration time is too far from current UTC time":**  
  Try running the script again.
- **"Invalid signature":**  
  Check your wallet credentials.

---

### 6. Security Tips

- Never share your worker name **before registration**.
- If your worker name is compromised, stop mining and restart with a new name.
- Use unique worker names for each mining instance.
- Register immediately after starting your miner.

---

### 7. Script Requirements

> The registration script requires:
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
