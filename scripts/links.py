from __future__ import annotations

import atexit
import os
import re
import subprocess
from typing import NamedTuple

import requests
from modules.shared import cmd_opts

LOCALHOST_RUN = "localhost.run"
REMOTE_MOE = "remote.moe"
SERVEO_NET = "serveo.net"
CLOUDFLARED = "trycloudflare.com"
localhostrun_pattern = re.compile(r"(?P<url>https?://\S+\.lhr\.life)")
remotemoe_pattern = re.compile(r"(?P<url>https?://\S+\.remote\.moe)")
serveonet_pattern = re.compile(r"(?P<url>https?://\S+\.serveo\.net)")
claudflare_pattern = re.compile(r"(?P<url>https?://\S+\.trycloudflare\.com)")
claudflare_metrics_pattern = re.compile(r"(?P<url>127\.0\.0\.1:\d+/metrics)")
claudflare_bin = os.path.join(os.path.dirname(__file__), 'claudflared')
links_file = '/content/links.txt'


def gen_key(key_name: str, key_dir: str | None = None) -> None:
    if key_dir is None:
        key_dir = os.path.join(os.path.expanduser('~'), '.ssh')
    if not os.path.exists(key_dir):
        os.makedirs(key_dir)

    private_key_path = os.path.join(key_dir, key_name)
    public_key_path = f"{private_key_path}.pub"
    if os.path.exists(private_key_path):
        os.remove(private_key_path)
    if os.path.exists(public_key_path):
        os.remove(public_key_path)
    args = [
        "ssh-keygen",
        "-t", "rsa",
        "-b", "4096",
        "-N", "",
        "-f", private_key_path,
        "-q"
    ]
    subprocess.run(args, check=True)
    os.chmod(private_key_path, 0o600)


def write_tunnel_url(tunnel_url):
    if os.path.exists(links_file):
        with open(links_file, 'a') as f:
            f.write(tunnel_url + '\n')
    else:
        with open(links_file, 'w') as f:
            f.write(tunnel_url + '\n')


def get_cloudflared_bin():
    api_url = 'https://api.github.com/repos/cloudflare/cloudflared/releases/latest'
    last_release = 'https://github.com/cloudflare/cloudflared/releases/download/2024.2.1/cloudflared-linux-amd64'
    response = requests.get(api_url)
    response.raise_for_status()
    latest_release = response.json()
    download_url = None
    for asset in latest_release['assets']:
        if 'cloudflared-linux-amd64' in asset['name']:
            download_url = asset['browser_download_url']
            break
    download_url = download_url if download_url else last_release
    if not os.path.isfile(claudflare_bin):
        response = requests.get(download_url)
        with open(claudflare_bin, 'wb') as f:
            f.write(response.content)
    os.chmod(claudflare_bin, 0o777)


class Urls(NamedTuple):
    tunnel: str
    process: subprocess.Popen


class TryCloudflare:
    def __init__(self):
        self.running: dict[int, Urls] = {}

    def __call__(self, port: int | str) -> Urls:

        get_cloudflared_bin()

        port = int(port)
        if port in self.running:
            urls = self.running[port]
            return urls

        args = [claudflare_bin, "tunnel", "--url", f"http://127.0.0.1:{port}"]

        cloudflared = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, encoding="utf-8")

        atexit.register(cloudflared.terminate)
        tunnel_url = ""
        lines = 20
        for _ in range(lines):
            line = cloudflared.stderr.readline()
            url_match = claudflare_pattern.search(line)
            if url_match:
                tunnel_url = url_match.group("url")
            if tunnel_url:
                break
        else:
            RuntimeError("не получилось поднять туннель до клаудфлары")

        urls = Urls(tunnel_url, cloudflared)
        self.running[port] = urls
        return urls

    @staticmethod
    def _print(tunnel_url: str) -> None:
        print(f"ссылка на флару: {tunnel_url}")

    def terminate(self, port: int | str) -> None:
        port = int(port)
        if port in self.running:
            self.running[port].process.terminate()
            atexit.unregister(self.running[port].process.terminate)
            del self.running[port]
        else:
            print(f"на порту {port!r} не запущен туннель")


try_cloudflare = TryCloudflare()
gen_key("id_rsa")


def ssh_tunnel(host: str) -> str:
    port = cmd_opts.port if cmd_opts.port else 7860
    if host != CLOUDFLARED:
        args = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", f"80:127.0.0.1:{port}", host]
        tunnel = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")
        atexit.register(tunnel.terminate)
        tunnel_url = ""
        pattern = localhostrun_pattern if host == LOCALHOST_RUN else (remotemoe_pattern if host == REMOTE_MOE else serveonet_pattern)
        while True:
            line = tunnel.stdout.readline()
            if not line:
                break
            if line.startswith("Warning"):
                print(line, end="")
            url_match = pattern.search(line)
            if url_match:
                tunnel_url = url_match.group("url")
                break
        if not tunnel_url:
            tunnel_url = f"не удалось поднять туннель {host}"
    else:
        try:
            tunnel_url = try_cloudflare(port=port).tunnel
        except:
            tunnel_url = f"не удалось поднять туннель {host}"

    write_tunnel_url(tunnel_url)
    return tunnel_url


if cmd_opts.remotemoe:
    moe_url = ssh_tunnel(REMOTE_MOE)
    write_tunnel_url("готово!")
if cmd_opts.lhr_life:
    lhr_url = ssh_tunnel(LOCALHOST_RUN)
    write_tunnel_url("готово!")
if cmd_opts.serveo:
    serveo_url = ssh_tunnel(SERVEO_NET)
    write_tunnel_url("готово!")
if cmd_opts.flara:
    flare_url = ssh_tunnel(CLOUDFLARED)
    write_tunnel_url("готово!")
if cmd_opts.all_links:
    lhr_url = ssh_tunnel(LOCALHOST_RUN)
    moe_url = ssh_tunnel(REMOTE_MOE)
    serveo_url = ssh_tunnel(SERVEO_NET)
    flare_url = ssh_tunnel(CLOUDFLARED)
    write_tunnel_url("готово!")
