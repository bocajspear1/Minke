from images.base import BaseContainer
import json 
import os

class DetectItEasy(BaseContainer):

    def __init__(self, name):
        super().__init__('detect-it-easy', name)

    def process(self, job_dir):
        self.extract("/tmp/output.json", job_dir)
        self.extract("/tmp/hashes", job_dir)

        die_output = open(os.path.join(job_dir, "output.json"))
        die_data = json.load(die_output)
        die_output.close()

        output = {
            "arch": "UNKNOWN",
            "bits": "UNKNOWN",
            "hashes": {
                "sha256": "",
                "sha1": "",
                "md5": ""
            },
            "filetype": "UNKNOWN",
            "form": "UNKNOWN",
            "compiler": "UNKNOWN"
        }

        if "detects" in die_data:
            detect = die_data['detects'][0]
            if "filetype" in detect:
                output["filetype"] = detect["filetype"].lower()

            if "values" in detect:

                for item in detect['values']:
                    if item['type'] == "Compiler":
                        output["compiler"] = item['version']
                        info_data = item["info"]
                        info_split = info_data.split(" ", 1)
                        if info_split[0] == "EXEC":
                            output["form"] = "executable"
                        elif info_split[0] == "DYN":
                            output["form"] = "library"
                        
                        arch_split = info_split[1].split('-')
                        output['arch'] = arch_split[0].lower()
                        output['bits'] = arch_split[1].lower()


        hash_output = open(os.path.join(job_dir, "hashes"))
        hash_data = hash_output.read()
        hash_output.close()

        hash_lines = hash_data.split("\n")
        md5sum = hash_lines[0].split(" ")[0]
        sha1sum = hash_lines[1].split(" ")[0]
        sha256sum = hash_lines[2].split(" ")[0]

        output['hashes']['md5'] = md5sum
        output['hashes']['sha1'] = sha1sum
        output['hashes']['sha256'] = sha256sum
        
        output_file = open(os.path.join(job_dir, "info.json"), "w+")
        output_file.write(json.dumps(output, indent="   "))
        output_file.close()

        return output



        




