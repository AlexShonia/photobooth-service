import requests
import time
import json

BASE_URL = "http://127.0.0.1:6678/v104"

headers = {}


def open_pos():
    global headers

    payload = {
        "licenseToken": str(time.time()),
    }

    print("🔓 Opening POS session...")
    res = requests.post(f"{BASE_URL}/openpos", json=payload)
    res.raise_for_status()
    data = res.json()

    token = data.get("accessToken")
    if not token:
        raise Exception("❌ Failed to get accessToken from openpos.")

    access_token = token
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    print("✅ POS session opened with token.")


def close_pos():
    print("🚪 Closing POS session...")

    res = requests.post(f"{BASE_URL}/closepos", headers=headers)
    res.raise_for_status()
    print("✅ POS session closed.")


def unlock_device(amount_gel):

    payload = {
        "header": {"command": "UNLOCKDEVICE"},
        "params": {
            "posOperation": "AUTHORIZE",
            "amount": int(amount_gel * 100),
            "currencyCode": "981",
            "idleText": "მიადეთ ბარათი აპარატს",
            "language": "GE",
            "ecrVersion": "FunwellAI-BOG-v1.0",
            "operatorId": "admin",
            "operatorName": "Admin",
        },
    }

    print("unlock payload: ", payload)

    print("🔓 Unlocking terminal for payment...")
    res = requests.post(f"{BASE_URL}/executeposcmd", headers=headers, json=payload)
    res.raise_for_status()
    print(res.status_code)
    print("✅ Terminal unlocked.")


def unlock_device_nooperation():

    payload = {
        "header": {"command": "UNLOCKDEVICE"},
        "params": {
            "posOperation": "NOOPERATION",
            "amount": 999,
            "currencyCode": "981",
            "idleText": "გთხოვთ დაადეთ ბარათი",
            "language": "GE",
            "ecrVersion": "FunwellAI-BOG-v1.0",
            "operatorId": "admin",
            "operatorName": "Admin",
        },
    }

    print("🔓 Unlocking terminal for payment...")
    res = requests.post(f"{BASE_URL}/executeposcmd", headers=headers, json=payload)
    res.raise_for_status()
    print(res.status_code)
    print("✅ Terminal unlocked.")


def poll_for_oncard(timeout=30):
    print("📡 Polling for ONCARD event...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(
                f"{BASE_URL}/getevent?longPollingTimeout=3",
                headers=headers,
                timeout=12,
            )
            response.raise_for_status()
            data = response.json()
            print("event: ", data)

            if data.get("eventName") == "ONCARD":
                print("💳 ONCARD received!")
                return data["properties"]
            if (
                data.get("eventName") == "ONKBD"
                and data.get("properties").get("kbdKey") == "FR"
            ):
                raise Exception("Payment cancelled")
            else:
                print("⏳ Still waiting... Event:", data.get("eventName"))
        except Exception as e:
            print("⚠️ Polling error:", str(e))
            if str(e) == "Payment cancelled":
                raise e

        time.sleep(1)
    raise TimeoutError("Timed out waiting for ONCARD event.")


import uuid


def send_authorize(card_props, amount_gel):
    doc_number = str(uuid.uuid4())[:12]  # Unique doc number, max 30 chars
    pan4 = card_props.get("PAN", "")[-4:] if card_props.get("reqPAN4Digit") else ""

    payload = {
        "header": {"command": "AUTHORIZE"},
        "params": {
            "amount": int(amount_gel * 100),
            "cashBackAmount": 0,
            "currencyCode": "981",
            "documentNr": doc_number,
            "panL4Digit": pan4,
        },
    }

    print("📤 Sending AUTHORIZE...")
    res = requests.post(f"{BASE_URL}/executeposcmd", headers=headers, json=payload)
    res.raise_for_status()
    result = res.json()
    print("✅ AUTHORIZE response:", json.dumps(result, indent=2))
    return result


def send_selected_value(value: str):
    payload = {
        "header": {"command": "SETSELECTEDVALUE"},
        "params": {
            "selectedValue": value,
        },
    }

    print(f"🎯 Selecting value: {value}")
    res = requests.post(f"{BASE_URL}/executeposcmd", headers=headers, json=payload)
    res.raise_for_status()
    print("✅ Value selected.")


def wait_for_result():
    print("🕒 Waiting for ONTRNSTATUS and ONPRINT...")
    ontrnstatus_result = None

    while True:
        try:
            response = requests.get(
                f"{BASE_URL}/getevent?longPollingTimeout=3",
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            event = data.get("eventName")

            if event == "ONTRNSTATUS":
                print("✅ Transaction completed:", json.dumps(data, indent=2))
                ontrnstatus_result = data
                break

            elif event == "ONPRINT":
                print("🧾 Receipt event received.")

            elif event == "ONCARDREMOVE":
                print("❌ Card was removed or transaction cancelled.")
                break

            elif event == "ONSELECT":
                print("🔘 ONSELECT received:", json.dumps(data, indent=2))
                options = data.get("properties", {}).get("options", [])
                for opt in options:
                    if "Georgian Lari" in opt:
                        send_selected_value(opt)

            elif event:
                print("event result: ", data)
                print("⏳ Still waiting... Event:", event)

            time.sleep(1)
        except Exception as e:
            print("⚠️ Polling failed:", str(e))
            break

    return ontrnstatus_result


def close_doc_from_ontrnstatus(event_data):
    props = event_data.get("properties", {})
    op_id = props.get("operationId")
    doc_nr = props.get("documentNr")

    if not op_id or not doc_nr:
        print("❌ Cannot close doc: Missing operationId or documentNr.")
        return

    payload = {
        "header": {"command": "CLOSEDOC"},
        "params": {
            "operations": [op_id],
            "documentNr": doc_nr,
        },
    }

    for attempt in range(5):
        try:
            res = requests.post(
                f"{BASE_URL}/executeposcmd", headers=headers, json=payload
            )
            res.raise_for_status()
            result = res.json()
            if result.get("resultCode") == "OK":
                print("result: ", result)
                print("✅ CLOSEDOC confirmed.")
                return
            print("⚠️ CLOSEDOC attempt failed:", result)
        except Exception as e:
            print("⚠️ CLOSEDOC exception:", e)
        time.sleep(2)


def lock_device():
    payload = {
        "header": {"command": "LOCKDEVICE"},
        "params": {
            "idleText": "სალარო აპარატი ჩართულია",
        },
    }

    print("🔓Locking terminal🔓")
    res = requests.post(f"{BASE_URL}/executeposcmd", headers=headers, json=payload)
    res.raise_for_status()
    print(res.status_code)
    print("✅ Terminal Locked.")


def send_void(operation_id):
    payload = {"header": {"command": "VOID"}, "params": {"operationId": operation_id}}

    try:
        print(f"🧨 Sending VOID for operation {operation_id}...")
        res = requests.post(f"{BASE_URL}/executeposcmd", headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()
        print("void response: ", data)
        if data.get("resultCode") == "OK":
            print("✅ VOID successful.")
        else:
            print("⚠️ VOID failed:", data)
    except Exception as e:
        print("❌ VOID request failed:", str(e))


def close_day(operator_id="admin", operator_name="Admin"):
    payload = {
        "header": {"command": "CLOSEDAY"},
        "params": {"operatorId": operator_id, "operatorName": operator_name},
    }

    print("📅 Sending CLOSE DAY command...")
    try:
        response = requests.post(
            f"{BASE_URL}/executeposcmd", headers=headers, json=payload, timeout=15
        )
        response.raise_for_status()
        result = response.json()

        if result.get("resultCode") == "OK":
            print("✅ Day closed successfully.", result)
        else:
            print("⚠️ CLOSE DAY failed:", result)

    except Exception as e:
        print("❌ CLOSE DAY error:", str(e))


def run_pos_payment(amount):
    ontrnstatus = ""
    print("amount in pos: ", amount)

    try:
        open_pos()
        unlock_device(amount)
        card_info = poll_for_oncard()
        if not card_info.get("allowAuthorize", False):
            print("❌ Card not allowed for payment.")
            return
        authorize_result = send_authorize(card_info, amount)
        ontrnstatus = wait_for_result()

        if ontrnstatus:
            operation_id = ontrnstatus.get("properties", {}).get("operationId")
            if not operation_id:
                print("❌ Missing operationId in ONTRNSTATUS.")
                return

        else:
            print(
                "❌ No ONTRNSTATUS received. Transaction may have failed or been cancelled."
            )

    except Exception as e:
        print("❌ Payment failed:", str(e))

    finally:
        if ontrnstatus:
            close_doc_from_ontrnstatus(ontrnstatus)

        lock_device()
        close_pos()
