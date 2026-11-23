# Soundbar Remote

A retro web remote for the Bestisan S6520C. The website includes a demo for power, mute, volume, input, sound modes, tone, and playback. The controls in live mode send learned infrared commands through a Broadlink blaster. The soundbar uses one-way infrared, so the website reports transmissions and demo state only.

## Preview and GitHub Pages

Open `docs/index.html` in a browser to try the demo. To publish it, go to the repository’s **Settings → Pages**, choose **Deploy from a branch**, and select **main** and **/docs**.

## Control your soundbar

Use a Python 3 computer, a Broadlink RM Mini or RM Pro already joined to Wi-Fi, and the original remote or a compatible replacement for learning. Place the blaster where it can see the soundbar. Find its IPv4 address in your router or Broadlink app.

From the repository folder, install the bridge dependency in a virtual environment.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, use `.venv\Scripts\Activate.ps1` to activate the environment.

Replace the example IP with the blaster’s address. After each learning command, point the physical remote at the **blaster** and press the matching button.

```sh
python bridge.py --blaster 192.168.1.42 learn power
python bridge.py --blaster 192.168.1.42 learn volume_up
python bridge.py --blaster 192.168.1.42 learn volume_down
python bridge.py --blaster 192.168.1.42 serve
```

Open the URL the bridge prints. Run `python bridge.py --blaster 192.168.1.42 learn --help` to see every button name. Teach only buttons available on your physical remote and restart the bridge after training. The learned signals stay in `codes.local.json` on the computer.

For phone use, pass `--listen` followed by the computer’s own LAN IP after `serve`. Open the printed URL from your phone on the same Wi-Fi. Use this mode on a trusted home network because anyone on that network who can reach the bridge can operate the remote. Keep the bridge off the public internet.

If learning or sending fails, check that both devices are on the same local network, verify the IP, and check the blaster’s device lock in its app.
