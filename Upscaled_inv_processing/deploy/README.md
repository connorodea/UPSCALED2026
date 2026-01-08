# Upscaled Inventory Deployment

## 1) Copy repo to server

Recommended path: `/opt/upscaled/Upscaled_inv_processing`

## 2) Configure environment

Copy the env example:

```bash
sudo mkdir -p /etc/upscaled
sudo cp deploy/env.example /etc/upscaled/inventory.env
sudo nano /etc/upscaled/inventory.env
```

Set `UPSCALED_WEB_PASSWORD` or `UPSCALED_USERS` (JSON array).

Example users:

```
UPSCALED_USERS='[{"username":"admin","password":"change-me","role":"admin"},{"username":"staff","password":"change-me","role":"staff"}]'
```

## 3) Install + start services

```bash
sudo bash deploy/install.sh
```

## 4) Nginx + SSL

```bash
sudo cp deploy/nginx/inventory.upscaledinc.com.conf /etc/nginx/sites-available/inventory.upscaledinc.com
sudo ln -s /etc/nginx/sites-available/inventory.upscaledinc.com /etc/nginx/sites-enabled/inventory.upscaledinc.com
sudo nginx -t
sudo systemctl reload nginx

sudo certbot --nginx -d inventory.upscaledinc.com
```

## 5) Optional: print agent (local machine)

Run locally where the printer is attached:

```bash
npm run print:dev
```

Point the server to the local agent:

```bash
export PRINT_MODE="proxy"
export PRINT_PROXY_URL="http://LOCAL_MACHINE:8788/print"
```

## Local machine bootstrap (one command)

From the repo root:

```bash
bash deploy/local_setup.sh
```

## Print agent installer (macOS unsigned)

```bash
bash deploy/print_agent/macos/build_macos_print_agent.sh
```

Then download it from:

```
http://inventory.upscaledinc.com/downloads/upscaled-print-agent-macos.pkg
```
