
import os
import re
import json
import subprocess

MAIN_MAUDE = os.path.join(os.path.dirname(__file__), '..', "semantics/main.maude")

def find_tfplan(path):
    if os.path.isfile(path) and path.endswith('.json'):
        return path
    elif os.path.isdir(path):
        # Search for JSON files containing 'plan*.json'
        planpath = None
        for item in os.listdir(path):
            if os.path.isfile(os.path.join(path,item)):
                if item.find("plan") >= 0 and item.endswith('.json'):
                    if not planpath or len(item) < len(planpath):
                        planpath = item
        if planpath:
            return os.path.join(path, planpath)


def new_maude_subprocess():
    pr = subprocess.Popen(
                    ["maude", "-no-advise", MAIN_MAUDE],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    text=True
                )
    pr.stderr = pr.stdout
    return pr


def call_maude_get_result(input_str: str, pr):
    input_str = input_str.rstrip()
    assert input_str.endswith("."), "Maude input command must end with '.'"

    rewrites_pattern = re.compile(r"rewrites: (\d+) in (\d+)ms cpu.*")

    input_str += "\nred 1 .\n"   # for a termination marker
    pr.stdin.write(input_str)
    pr.stdin.flush()

    for line in pr.stdout:
        if line.startswith("rewrites:"):
            break
    m = rewrites_pattern.match(line)
    nb_rewrites = int(m.group(1))
    time_in_ms = int(m.group(2))

    for line in pr.stdout:
        if line.startswith("result "):
            break
    res = line[line.index(": ")+1:-1]

    for line in pr.stdout:
        if not line.startswith("=========="):
            res += line
        else:
            break

    for line in pr.stdout:
        if line.startswith("result NzNat: 1"):
            break

    return res, (nb_rewrites, time_in_ms)


def render_mermaid_pictures(mmd_files):
    print("Rendering Mermaid pictures...")
    outformat = "png" # "pdf"
    os.chmod(out_path, 0o777)
    for mmd_file in files:
        print(f"Rendering {mmd_file} as .{outformat}")
        mmd_rendered = f"{os.path.splitext(mmd_file)[0]}.{outformat}"
        MERMAID_BIN = [ "docker", "run", "--rm", f"-v{os.getcwd()}:/data", "minlag/mermaid-cli:11.12.0" ]
        p = subprocess.run(MERMAID_BIN + [f"-i{mmd_file}", f"-o{mmd_rendered}", "--outputFormat", outformat, "--pdfFit"])
        # os.chown(mmd_rendered, os.getuid(), os.getgid())
    os.chmod(out_path, 0o755)


