'''
This script transforms all full-staves format to MIDI melody and harmony.
The output MIDI files have two tracks: first track melody second track
chords. All pieces are transformed to C major and A minor.
'''

from music21 import converter, stream, note, chord, interval, pitch, instrument
import os

def load_score(xml_path):
    return converter.parse(xml_path)
# end load_score

def extract_skyline_melody(part):
    melody = stream.Part()
    clef = part.getElementsByClass('Clef').first()
    if clef is not None:
        melody.insert(0, clef)
    ts = part.getTimeSignatures().first()
    if ts is not None:
        melody.insert(0, ts)

    # group notes by offset
    offset_dict = {}
    for n in part.flat.recurse().notes:
        offset_dict.setdefault(n.offset, []).append(n)
    
    for offset, notes in sorted(offset_dict.items()):
        pitches = []
        for n in notes:
            if isinstance(n, note.Note):
                pitches.append(n)
            elif isinstance(n, chord.Chord):
                for n in n.notes:
                    pitches.append(n)
        highest = max(pitches, key=lambda n: n.pitch.midi)
        melody.insert(offset, note.Note(
            highest.pitch,
            quarterLength=highest.quarterLength
        ))

    return melody
# end extract_skyline_melody

def estimate_key_from_cluster(part):
    pitches = []
    for n in part.recurse().notes:
        if isinstance(n, note.Note):
            pitches.append(n)
        elif isinstance(n, chord.Chord):
            for n in n.notes:
                pitches.append(n)
    pitches = sorted(
        pitches,
        key=lambda p: p.pitch.midi
    )

    root = pitches[0]
    intervals_above_root = {p.pitch.midi - root.pitch.midi for p in pitches}

    is_major = 4 in intervals_above_root
    is_minor = 3 in intervals_above_root

    if is_major and not is_minor:
        mode = 'major'
    elif is_minor and not is_major:
        mode = 'minor'
    else:
        # fallback heuristic
        mode = 'major'

    return root, mode
# end estimate_key_from_cluster

def merge_parts_parallel(part_a, part_b):
    merged = stream.Part()

    for el in part_a.flatten().notesAndRests:
        merged.insert(el.offset, el)

    for el in part_b.flatten().notesAndRests:
        merged.insert(el.offset, el)

    return merged
# end merge_parts_parallel

def extract_chords(part5, part6):
    combined = merge_parts_parallel(part5, part6)

    chordified = combined.chordify()

    chords = stream.Part()
    for c in chordified.recurse().getElementsByClass(chord.Chord):
        chords.insert(c.offset, chord.Chord(
            c.pitches,
            quarterLength=c.quarterLength
        ))

    return chords
# end extract_chords

def compute_transposition_interval(root, mode):
    if mode == 'major':
        target = pitch.Pitch('C')
    else:
        target = pitch.Pitch('A')

    return interval.Interval(root, target)
# end compute_transposition_interval

def export_to_midi(melody, chords, interval_obj, out_path):
    score = stream.Score()

    melody_t = melody.transpose(interval_obj)
    chords_t = chords.transpose(interval_obj)

    melody_t.insert(0, instrument.Instrument())
    chords_t.insert(0, instrument.Instrument())

    # merged_parts = merge_parts_parallel(melody_t, chords_t)

    score.insert(0, melody_t)
    score.insert(0, chords_t)
    # score.insert(0, merged_parts)

    score.write('midi', out_path)
# end export_to_midi

def normalize_pickup_across_parts(score):
    # assume global time signature
    ts = score.recurse().getElementsByClass('TimeSignature').first()
    bar_len = ts.barDuration.quarterLength

    for part in score.parts:
        m1 = part.measure(0)
        if m1 is None:
            continue

        m1_len = m1.quarterLength

        if m1_len < bar_len:
            pickup_deficit = bar_len - m1_len
            part.shiftElements(pickup_deficit)
# end normalize_pickup_across_parts

def process_xml_to_harmonization_midi(xml_path, out_midi_path):
    score = load_score(xml_path)
    normalize_pickup_across_parts(score)

    part1 = score.parts[0]
    part3 = score.parts[2]
    part5 = score.parts[4]
    part6 = score.parts[5]

    melody = extract_skyline_melody(part1)
    root, mode = estimate_key_from_cluster(part3)
    chords = extract_chords(part5, part6)

    transposition = compute_transposition_interval(root, mode)
    export_to_midi(melody, chords, transposition, out_midi_path)
# end process_xml_to_harmonization_midi


if __name__ == '__main__':
    parent_path = 'xml_full_staves'
    destination_path = 'midi_two_parts'
    os.makedirs(destination_path, exist_ok=True)
    idioms_list = os.listdir(parent_path)
    for i in idioms_list:
        if i[0] != '.':
            tmp_source_path = os.path.join(parent_path, i)
            tmp_destination_path = os.path.join(destination_path, i)
            os.makedirs(tmp_destination_path, exist_ok=True)
            xml_files = os.listdir(tmp_source_path)
            for f in xml_files:
                if f[0] != '.':
                    xml_path = os.path.join(tmp_source_path, f)
                    midi_file_name = os.path.splitext(f)[0] + '.mid'
                    out_midi_path = os.path.join(tmp_destination_path, midi_file_name)
                    try:
                        process_xml_to_harmonization_midi(xml_path, out_midi_path)
                    except:
                        print(xml_path)
                        # xml_full_staves/Impressionistic/impress2_debussy.xml
                        # xml_full_staves/organum/organum_par.xml