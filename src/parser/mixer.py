"""Extract mixer information from Ableton Live XML."""


def extract_mixer_from_track(track_elem):
    """
    Extract mixer settings from a track element.

    Args:
        track_elem: ElementTree element for a track (AudioTrack, MidiTrack, etc.)

    Returns:
        Dict with mixer settings:
        {
            'volume': float,           # 0.0 to 1.0+
            'pan': float,              # -1.0 (left) to 1.0 (right)
            'sends': [                 # List of send levels
                {
                    'index': int,
                    'level': float,    # 0.0 to 1.0
                    'is_active': bool
                }
            ],
            'crossfader': str,         # 'A', 'B', or 'None'
            'is_muted': bool,
            'is_soloed': bool
        }
    """
    mixer_elem = track_elem.find('.//DeviceChain/Mixer')
    if mixer_elem is None:
        return None

    # Extract volume
    volume_elem = mixer_elem.find('.//Volume/Manual')
    volume = float(volume_elem.get('Value', 1.0)) if volume_elem is not None else 1.0

    # Extract pan
    pan_elem = mixer_elem.find('.//Pan/Manual')
    pan = float(pan_elem.get('Value', 0.0)) if pan_elem is not None else 0.0

    # Extract sends
    sends = []
    send_holders = mixer_elem.findall('.//Sends/TrackSendHolder')
    for index, send_holder in enumerate(send_holders):
        send_manual = send_holder.find('.//Manual')
        send_on = send_holder.find('.//On')

        level = float(send_manual.get('Value', 0.0)) if send_manual is not None else 0.0
        is_active = (send_on.get('Value', 'true').lower() == 'true'
                    if send_on is not None else True)

        sends.append({
            'index': index,
            'level': level,
            'is_active': is_active
        })

    # Extract crossfader assignment
    crossfader_elem = mixer_elem.find('.//Speaker/Crossfader')
    crossfader = 'None'
    if crossfader_elem is not None:
        crossfader_val = int(crossfader_elem.get('Value', 1))
        if crossfader_val == 0:
            crossfader = 'A'
        elif crossfader_val == 2:
            crossfader = 'B'
        else:
            crossfader = 'None'

    # Extract mute/solo state (from track level, not mixer)
    is_muted = False
    is_soloed = False

    # Check for mute state
    mute_elem = track_elem.find('.//TrackMute/Manual')
    if mute_elem is not None:
        is_muted = mute_elem.get('Value', 'false').lower() == 'true'

    # Check for solo state
    solo_elem = track_elem.find('.//Solo/Manual')
    if solo_elem is not None:
        is_soloed = solo_elem.get('Value', 'false').lower() == 'true'

    mixer_data = {
        'volume': volume,
        'pan': pan,
        'sends': sends,
        'crossfader': crossfader,
        'is_muted': is_muted,
        'is_soloed': is_soloed
    }

    return mixer_data
