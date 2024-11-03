#!/usr/bin/env python3
"""
Script to watch streams from http://www.teleboy.ch
Copyright: Elmar Meyer, 2024 - 2034
License:   GPL-3
"""

# User Account with Teleboy.ch
user     = '<your username>'
password = '<your password>'


from MPV import MPV
import asyncio
import re
import requests
import json
from urllib.parse import urlsplit, urlunsplit

evnt = asyncio.Event()
evnt.clear()


def __transform_url_into_non_drm_form(url):
    """
    This is an attempt to fix this issue:
    https://github.com/reduzent/watchteleboy/issues/34
    We simply try to transform URLs of drm-protected manifests to non-drm manifest
    by replacing the server and the manifest file.
    """
    u_elements = list(urlsplit(url))
    server_elements = u_elements[1].split('.')
    host_elements = server_elements[0].split('-')
    if (host_elements[2]) == 'dashenc':
        host_elements[2] = 'dash'
        server_elements[0] = '-'.join(host_elements)
        u_elements[1] = '.'.join(server_elements)
        path_elements = u_elements[2].split('/')
        path_elements[2] = 'm.mpd'
        u_elements[2] = '/'.join(path_elements)
        url = urlunsplit(u_elements)
    return(url)


class CECAdapter:
    def __init__(self, polltime):
        self._polltime= polltime
        self._queue = asyncio.Queue()
        self._running = False

    def setPauseCallback(self,PauseCallback):
        self.PauseCallback = PauseCallback

    def setShowTextCallback(self,ShowTextCallback):
        self.ShowTextCallback = ShowTextCallback

    def setChannelCountCallback(self,ChannelCountCallback):
        self.ChannelCountCallback = ChannelCountCallback

    async def nextCmd(self):
        return await self._queue.get()

    async def start(self):
        ch = None
        ch_last = 1
        ch_current = 1
        pattern_key = '(?<=Key ).*?(?=:)'
        cmd = ["stdbuf","-i0","-o0","-e0","cec-client"] # unbuffered cmd
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        #stdin, stdout, stderr = await proc.communicate()

        proc.stdin.write(b"tx 10:47:54:65:6C:65:62:6F:79:20:54:56\n")
        await proc.stdin.drain()
        await asyncio.sleep(2)

        proc.stdin.write(b"as\n")
        await proc.stdin.drain()

        await evnt.wait()
        ChannelCount = await self.ChannelCountCallback()

        self._running = True
        while self._running:
            line = None
            try:
                line = await asyncio.wait_for(proc.stdout.readline(), self._polltime)
            except asyncio.TimeoutError:
                if ch is not None:
                    ch_last = ch_current
                    await self._queue.put(ch)
                    ch_current = ch
                    ch = None
                continue
            m = re.search(pattern_key,line.decode())
            if m:
                key = line[m.start():m.end()]
                match key:
                    case b'select':
                        if ch is not None:
                            ch_last = ch_current
                            await self._queue.put(ch)
                            ch_current = ch
                            ch = None
                    case b'right':
                        pass
                    case b'left':
                        pass
                    case b'up':
                        pass
                    case b'down':
                        pass
                    case b'F1 (blue)':
                        pass
                    case b'F2 (blue)':
                        pass
                    case b'F3 (blue)':
                        pass
                    case b'F4 (blue)':
                        pass
                    case b'pause':
                        await self.PauseCallback(True)
                    case b'play':
                        await self.PauseCallback(False)
                    case b'previous channel':
                        ch = ch_last
                        ch_last = ch_current
                        await self._queue.put(ch)
                        ch_current = ch
                        await self.ShowTextCallback(f'{ch}/{ChannelCount}')
                        ch = None
                    case b'channel up':
                        ch = ch_current
                        ch += 1
                        if ch>ChannelCount:
                            ch = ChannelCount
                        ch_last = ch_current
                        await self._queue.put(ch)
                        ch_current = ch
                        await self.ShowTextCallback(f'{ch}/{ChannelCount}')
                        ch = None
                    case b'channel down':
                        ch = ch_current
                        ch -= 1
                        if ch<1:
                            ch = 1
                        ch_last = ch_current
                        await self._queue.put(ch)
                        ch_current = ch
                        await self.ShowTextCallback(f'{ch}/{ChannelCount}')
                        ch = None
                    case b'0' | b'1' | b'2' | b'3' | b'4' | b'5' | b'6' | b'7' | b'8' | b'9':
                        if ch is None:
                            ch = 0
                        ch = 10*ch + int(key)
                        if ch<1:
                            ch = 1
                        elif ch>ChannelCount:
                            ch = ChannelCount
                        await self.ShowTextCallback(f'{ch}/{ChannelCount}')
                    case _:
                        await self.ShowTextCallback(f'{key}')

    def stop(self):
        self._running = False

adapter = CECAdapter(1.5)




class MyMPV(MPV):
    def __init__(
            self,
            media="",
            socket=None,
            mpv_path="/usr/bin/mpv",
            mpv_args=["--no-audio-display"],
            log_callback=None,
            log_level="error"):
        super().__init__(media,socket,mpv_path,mpv_args,log_callback,log_level)
        self._pause = False

    async def run(self):
        await self.start()
        await asyncio.sleep(1)
        await self.command("loadfile", self.media, "replace")
        await asyncio.sleep(3)
        evnt.set()
        await self._CecProcessing()

    async def PlayList(self, pos):
        await self.command("set_property", "playlist-pos", pos)

    async def PlayListNext(self):
        await self.command("set_property", "playlist_next")

    async def PlayListPrevious(self):
        await self.command("set_property", "playlist_prev")

    async def SetPause(self, state):
        if self._pause==state:
            return
        self._pause = state
        await self.command("cycle", "pause")

    async def ShowText(self,text):
        await self.command("show-text",str(text),3000)

    async def ChannelCount(self):
        return await self.command("get_property", "playlist-count")

    async def _CecProcessing(self):
        while True:
            ch = await adapter.nextCmd()
            if ch is None:
                continue
            await self.PlayList( ch-1 )


async def main():
    # replace M3U-File.
    user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0'
    login_url = 'https://www.teleboy.ch/login_check'
    userenv_url = 'https://www.teleboy.ch/live'
    headers = {
        'User-Agent': user_agent
    }
    api_key = 'e899f715940a209148f834702fc7f340b6b0496b62120b3ed9c9b3ec4d7dca00'

    session = requests.Session()
    session.headers.update(headers)

    data = {
        'login': user,
        'password': password,
        'keep_login': '1'
        }
    r_login = session.post(login_url, data=data)
    try:
        assert r_login.status_code != 429
    except AssertionError:
        print("Your login is blocked. Please login via browser and answer captcha.")
        print("Visit https://www.teleboy.ch/ and try again.")
        return False
    try:
        session.cookies['cinergy_auth']

        r_env = session.get(userenv_url)
        assert r_env.status_code == 200
        content = r_env.content.decode()
        uid_raw = re.findall(r'\s+\.setId\(\d+\)', content, re.MULTILINE)[0]
        user_id = uid_raw[uid_raw.find('(')+1:uid_raw.find(')')]
        session_id = session.cookies['cinergy_s']
        headers = {
            'x-teleboy-apikey': api_key,
            'x-teleboy-session': session_id
        }
        session.headers.update(headers)
        api_channellist_url = f'https://tv.api.teleboy.ch/users/'\
                              f'{user_id}/broadcasts/now?expand=station&stream=true'
        r_api = session.get(api_channellist_url)
        try:
            assert r_api.status_code == 200
        except AssertionError:
            print('failed to retrieve channel ids')
            return False
        channels = json.loads(r_api.content.decode())
    except KeyError:
        print('Login failed')
        return False

    counter=0
    m3u = open('PlayList.m3u', 'w')
    for ch in channels['data']['items']:
        stream = ch['station_label']
        station_id = ch['station_id']

        api_url = f'https://tv.api.teleboy.ch/users/{user_id}/stream/live/{station_id}'
        r_api = session.get(api_url)
        try:
            assert r_api.status_code == 200
        except AssertionError:
            print('failed to retrieve channel data')
        channel_data = json.loads(r_api.content.decode())
        url = __transform_url_into_non_drm_form(channel_data['data']['stream']['url'])
        counter += 1
        m3u.write('#EXTINF:'+str(counter)+', '+stream+'\n')
        m3u.write(url+'\n')
    m3u.close()

    # Open the video player and load a file.
    try:
        mpv = MyMPV(media='PlayList.m3u', mpv_args=['--no-audio-display','--window-maximized=yes','--fullscreen=yes','--cache=yes','--cache-secs=6000','--demuxer-max-bytes=8GiB','--profile=low-latency'])
    except IndexError:
        raise SystemExit("usage: python example.py <path>")
    adapter.setChannelCountCallback(mpv.ChannelCount)
    adapter.setShowTextCallback(mpv.ShowText)
    adapter.setPauseCallback(mpv.SetPause)
    await asyncio.gather(mpv.run(), adapter.start())


if __name__ == "__main__":
    # Start playback.
    asyncio.run(main())
    asyncio.run_until_complete()
