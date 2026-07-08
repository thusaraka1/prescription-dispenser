# ==========================================
# SMD Kiosk — Flask Server
# ==========================================
# Serves the kiosk touchscreen UI and provides
# API endpoints for Firebase data and hardware control.

import logging
import threading
import json
from flask import Flask, render_template, jsonify, request
import requests as http_requests

from config import (
    FIREBASE_URL, FLASK_HOST, FLASK_PORT, FLASK_DEBUG,
    MANUAL_MIN_QUANTITY, MANUAL_MAX_QUANTITY
)
from hardware import HardwareController

# ---- Logging Setup ----
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ---- Flask App ----
app = Flask(__name__)

# ---- Hardware Controller ----
hw = HardwareController()

# ---- Dispensing state (thread-safe) ----
dispense_lock = threading.Lock()
dispense_status = {
    'active': False,
    'current_medicine': '',
    'current_progress': 0,
    'total_progress': 0,
    'medicines_completed': 0,
    'medicines_total': 0,
    'message': ''
}


# ==========================================
# Page Routes
# ==========================================

@app.route('/')
def index():
    """Serve the kiosk single-page application."""
    return render_template('kiosk.html')


# ==========================================
# API Routes — Firebase Data
# ==========================================

@app.route('/api/prescription/<barcode_id>')
def get_prescription(barcode_id):
    """
    Fetch a prescription from Firebase by its barcode ID.
    Returns patient details and medication list.
    """
    try:
        url = f"{FIREBASE_URL}/prescriptions/{barcode_id}.json"
        response = http_requests.get(url, timeout=10)
        data = response.json()

        if data is None:
            return jsonify({
                'success': False,
                'error': 'Prescription not found',
                'message': f'No prescription found for barcode: {barcode_id}'
            }), 404

        return jsonify({
            'success': True,
            'prescription': data
        })

    except http_requests.exceptions.Timeout:
        logger.error(f"Firebase timeout for barcode: {barcode_id}")
        return jsonify({
            'success': False,
            'error': 'Connection timeout',
            'message': 'Could not connect to database. Please try again.'
        }), 504

    except Exception as e:
        logger.error(f"Error fetching prescription: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'An error occurred while fetching the prescription.'
        }), 500


@app.route('/api/medicines')
def get_medicines():
    """Fetch all available medicines from Firebase."""
    try:
        url = f"{FIREBASE_URL}/medicines.json"
        response = http_requests.get(url, timeout=10)
        data = response.json()

        medicines = []
        if data:
            for key, value in data.items():
                medicines.append({
                    'id': key,
                    **value
                })

        return jsonify({
            'success': True,
            'medicines': medicines,
            'limits': {
                'min': MANUAL_MIN_QUANTITY,
                'max': MANUAL_MAX_QUANTITY
            }
        })

    except Exception as e:
        logger.error(f"Error fetching medicines: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/prescription/<barcode_id>/status', methods=['PATCH'])
def update_prescription_status(barcode_id):
    """Update a prescription's status in Firebase (e.g., mark as Dispersed)."""
    try:
        body = request.get_json()
        status = body.get('status', 'Dispersed')

        url = f"{FIREBASE_URL}/prescriptions/{barcode_id}.json"
        response = http_requests.patch(
            url,
            json={'status': status},
            timeout=10
        )

        if response.status_code == 200:
            logger.info(f"✅ Prescription {barcode_id} marked as '{status}'")
            return jsonify({'success': True, 'status': status})
        else:
            return jsonify({
                'success': False,
                'error': f'Firebase returned {response.status_code}'
            }), 500

    except Exception as e:
        logger.error(f"Error updating prescription status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==========================================
# API Routes — Dispensing
# ==========================================

@app.route('/api/dispense', methods=['POST'])
def dispense_prescription():
    """
    Dispense medicines from a prescription (barcode flow).
    Expects JSON body: { barcode_id: string, medicines: [{name, slot, totalQuantity}] }
    Runs dispensing in a background thread.
    """
    global dispense_status

    if dispense_status['active']:
        return jsonify({
            'success': False,
            'error': 'Dispensing already in progress'
        }), 409

    body = request.get_json()
    barcode_id = body.get('barcode_id')
    medicines = body.get('medicines', [])

    if not medicines:
        return jsonify({'success': False, 'error': 'No medicines to dispense'}), 400

    # Start dispensing in background thread
    thread = threading.Thread(
        target=_run_dispense,
        args=(barcode_id, medicines),
        daemon=True
    )
    thread.start()

    return jsonify({'success': True, 'message': 'Dispensing started'})


@app.route('/api/dispense/manual', methods=['POST'])
def dispense_manual():
    """
    Dispense a manually selected medicine.
    Expects JSON body: { medicine_name: string, quantity: int, slot: int }
    """
    global dispense_status

    if dispense_status['active']:
        return jsonify({
            'success': False,
            'error': 'Dispensing already in progress'
        }), 409

    body = request.get_json()
    medicine_name = body.get('medicine_name', 'Unknown')
    quantity = body.get('quantity', MANUAL_MIN_QUANTITY)
    slot = body.get('slot', 0)

    # Clamp quantity within limits
    quantity = max(MANUAL_MIN_QUANTITY, min(MANUAL_MAX_QUANTITY, quantity))

    medicines = [{
        'name': medicine_name,
        'slot': slot,
        'totalQuantity': quantity
    }]

    thread = threading.Thread(
        target=_run_dispense,
        args=(None, medicines),
        daemon=True
    )
    thread.start()

    return jsonify({'success': True, 'message': 'Manual dispensing started'})


@app.route('/api/dispense/status')
def get_dispense_status():
    """Get the current dispensing progress."""
    return jsonify(dispense_status)


def _run_dispense(barcode_id, medicines):
    """
    Background task: dispense medicines sequentially.
    Updates dispense_status for real-time progress polling.
    """
    global dispense_status

    with dispense_lock:
        total_medicines = len(medicines)
        dispense_status = {
            'active': True,
            'current_medicine': '',
            'current_progress': 0,
            'total_progress': 0,
            'medicines_completed': 0,
            'medicines_total': total_medicines,
            'message': 'Starting dispensing...'
        }

        total_units = sum(m.get('totalQuantity', 0) for m in medicines)
        units_dispensed = 0

        for idx, med in enumerate(medicines):
            name = med.get('name', 'Unknown')
            slot = med.get('slot', idx % len(hw.servo_pins))
            quantity = med.get('totalQuantity', 1)

            dispense_status['current_medicine'] = name
            dispense_status['current_progress'] = 0
            dispense_status['message'] = f'Dispensing {name}...'

            logger.info(f"🔄 [{idx + 1}/{total_medicines}] Dispensing {quantity}x {name} from slot {slot}")

            def on_progress(dispensed, total):
                nonlocal units_dispensed
                dispense_status['current_progress'] = int((dispensed / total) * 100)
                dispense_status['total_progress'] = int(
                    ((units_dispensed + dispensed) / total_units) * 100
                ) if total_units > 0 else 100

            result = hw.dispense(slot, quantity, progress_callback=on_progress)

            if result['success']:
                units_dispensed += quantity
                dispense_status['medicines_completed'] = idx + 1
                logger.info(f"✅ Completed: {name}")
            else:
                logger.error(f"❌ Failed to dispense {name}: {result.get('error')}")
                dispense_status['message'] = f'Error dispensing {name}'

        # Mark prescription as dispersed in Firebase
        if barcode_id:
            try:
                url = f"{FIREBASE_URL}/prescriptions/{barcode_id}.json"
                http_requests.patch(url, json={'status': 'Dispersed'}, timeout=10)
                logger.info(f"✅ Prescription {barcode_id} marked as Dispersed in Firebase")
            except Exception as e:
                logger.error(f"Failed to update Firebase status: {e}")

        dispense_status['active'] = False
        dispense_status['total_progress'] = 100
        dispense_status['message'] = 'All medications dispensed!'
        logger.info("🎉 All dispensing complete!")


# ==========================================
# Entry Point
# ==========================================

if __name__ == '__main__':
    print('')
    print('  +==================================================+')
    print('  |   Smart Medicine Dispenser (SMD)                  |')
    print(f'  |   Kiosk running on http://localhost:{FLASK_PORT}        |')
    print(f'  |   Simulation Mode: {hw.simulation}                    |')
    print('  +==================================================+')
    print('')

    try:
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
    except KeyboardInterrupt:
        hw.cleanup()
        print("\n👋 Kiosk server stopped.")
