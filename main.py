from onvif import ONVIFCamera
import cv2
from urllib.parse import urlparse, urlunparse
import time
import argparse
import tkinter as tk

ptz = None
token = None

def get_rtsp_url(ip, port, user, password):
    try:
        print(f"[+] Connecting to CCTV at {ip}:{port} ...")
        mycam = ONVIFCamera(ip, port, user, password)

        global ptz, token
        media_service = mycam.create_media_service()
        ptz = mycam.create_ptz_service()
        profile = media_service.GetProfiles()[0]
        token = profile.token

        stream_setup = media_service.create_type('GetStreamUri')
        stream_setup.StreamSetup = {
            'Stream': 'RTP-Unicast',
            'Transport': {'Protocol': 'RTSP'}
        }
        stream_setup.ProfileToken = token

        uri = media_service.GetStreamUri(stream_setup).Uri

        parsed = urlparse(uri)
        netloc = f"{user}:{password}@{parsed.hostname}:{parsed.port or 554}"
        new_uri = urlunparse((parsed.scheme, netloc, parsed.path, '', '', ''))

        print(f"[+] Final RTSP URL: {new_uri}")
        return new_uri
    except Exception as e:
        print(f"[!] Error getting RTSP URL: {e}")
        return None


def move_camera(pan, tilt, dur=0.2):
    try:
        req = ptz.create_type('ContinuousMove')
        req.ProfileToken = token
        req.Velocity = {
            'PanTilt': {'x': pan, 'y': tilt}
        }
        ptz.ContinuousMove(req)
        time.sleep(dur)
        stop_camera()
    except Exception as e:
        print(f"[!] PTZ Move Error: {e}")

def stop_camera():
    try:
        req = ptz.create_type('Stop')
        req.ProfileToken = token
        req.PanTilt = True
        req.Zoom = True
        ptz.Stop(req)
    except Exception as e:
        print(f"[!] Stop Error: {e}")


def stream_rtsp(rtsp_url):
    root = tk.Tk()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.destroy()

    win_width = int(screen_width * 0.8)
    win_height = int(screen_height * 0.8)

    print("[*] Starting video stream... Press 'q' to quit.")

    cv2.namedWindow('CCTV Live Stream', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('CCTV Live Stream', win_width, win_height)

    while True:
        cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            print("[!] Cannot open video stream. Retrying in 5 seconds...")
            time.sleep(5)
            continue

        while True:
            ret, frame = cap.read()
            if not ret:
                print("[!] Failed to grab frame. Reconnecting...")
                break

            cv2.imshow('CCTV Live Stream', frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                return
            elif key == ord('s'):
                print("[+] Stop Movement")
                stop_camera()
            elif key == 81:  # Left arrow
                print("[←] Pan Left")
                move_camera(-0.5, 0)
            elif key == 82:  # Up arrow
                print("[↑] Tilt Up")
                move_camera(0, 0.5)
            elif key == 83:  # Right arrow
                print("[→] Pan Right")
                move_camera(0.5, 0)
            elif key == 84:  # Down arrow
                print("[↓] Tilt Down")
                move_camera(0, -0.5)

        cap.release()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ONVIF CCTV Controller with PTZ and RTSP Stream")
    parser.add_argument('--ip', type=str, required=True, help='IP address of the CCTV')
    parser.add_argument('--port', type=int, default=2020, help='Port of the CCTV ONVIF service (default: 2020)')
    parser.add_argument('--user', type=str, required=True, help='Username for CCTV authentication')
    parser.add_argument('--password', type=str, required=True, help='Password for CCTV authentication')
    args = parser.parse_args()

    rtsp_url = get_rtsp_url(args.ip, args.port, args.user, args.password)
    if rtsp_url:
        stream_rtsp(rtsp_url)
