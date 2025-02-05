import mido, sys, json, os.path, math
from pydub import AudioSegment

def midi_note2hz(note: int) -> float:
    return 440 * 2 ** ((note - 69) / 12)

def get_time(time):
    sec = 0.0
    beat = time
    for i, e in enumerate(bpm_list):
        bpmv = e["bpm"]
        if i != len(bpm_list) - 1:
            et_beat = bpm_list[i + 1]["time"] - e["time"]
            if beat >= et_beat:
                sec += et_beat / tpb * (60 / bpmv)
                beat -= et_beat
            else:
                sec += beat / tpb * (60 / bpmv)
                break
        else:
            sec += beat / tpb * (60 / bpmv)
    return sec

if len(sys.argv) != 3:
    print("usage: python midi2phi.py <input-path> <output-path>")
    exit(1)

mid = mido.MidiFile(sys.argv[1])

chart = {
        "formatVersion": 3,
        "offset": 0.0,
        "judgeLineList": [
            {
                "bpm": 1875,
                "judgeLineMoveEvents": [
                    {
                        "startTime": -999999,
                        "endTime": 100000000,
                        "start": 0.5,
                        "start2": 0.1,
                        "end": 0.5,
                        "end2": 0.1
                    }
                ],
                "judgeLineRotateEvents": [
                    {
                        "startTime": -999999,
                        "endTime": 100000000,
                        "start": 0,
                        "end": 0
                    }
                ],
                "judgeLineDisappearEvents": [
                    {
                        "startTime": -999999,
                        "endTime": 100000000,
                        "start": 1,
                        "end": 1,
                    }
                ],
                "speedEvents": [
                    {
                        "startTime": 0,
                        "endTime": 100000000,
                        "value": 2.2
                    }
                ],
                "notesAbove": [],
                "notesBelow": []
            }
        ]
    }

tpb = mid.ticks_per_beat


tempo = 100000000
notes = []
active_notes = {}


max_length = 0
current_time_s = 0

bpm_dict = {}
current_time = 0.
ticks_per_beat = mid.ticks_per_beat

print("获取bpm列表...")
for track in mid.tracks:
    for msg in track:
        if msg.type == "set_tempo":
            bpm = 60000000 / msg.tempo
            if current_time not in bpm_dict:
                bpm_dict[current_time] = bpm
        current_time += msg.time


bpm_list = [{"time": time, "bpm": bpm} for time, bpm in bpm_dict.items()]
print(bpm_list)

print("获取音符时间...")
for i, track in enumerate(mid.tracks):
    current_time = 0.
    for msg in track:
        current_time += msg.time
        match msg.type:
            case "note_on":
                if msg.note not in active_notes:
                    active_notes[msg.note] = {
                        "startTime": get_time(current_time)*1000,
                        "note": msg.note
                    }
            case "note_off":
                if msg.note in active_notes:
                    note = active_notes.pop(msg.note)
                    notes.append({
                        "startTime": note["startTime"],
                        "endTime": get_time(current_time)*1000,
                        "note": note["note"]
                    })
        current_time_s = get_time(current_time)
    max_length = max(current_time_s*1000+1000, max_length)
print(f"谱面时长：{max_length}")

notes.sort(key=lambda x: x["startTime"])
for i, note in enumerate(notes):
    print(f"生成note {i+1}/{len(notes)}{" "*100}", end="\r")
    use_time = note["endTime"]-note["startTime"]
    one_note_use_time = 1000/midi_note2hz(note["note"])
    chart["judgeLineList"][0]["notesAbove"].extend([{
        "type": 1,
        "time": note["startTime"]+one_note_use_time*j,
        "positionX": (note["note"]-64)/128/0.05625,
        "holdTime": 0,
        "speed": 1,
        "floorPosition": 2.2 * (note["startTime"]+one_note_use_time*j) / 1000
    } for j in range(math.ceil(use_time/one_note_use_time))])
print("\n正在写入文件...")
music = AudioSegment.silent(duration=max_length)
music.export(os.path.join(sys.argv[2], "music.wav"), format="wav")
with open(os.path.join(sys.argv[2], "chart.json"), "w") as f:
    json.dump(chart, f)