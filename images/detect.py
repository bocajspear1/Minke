from images.base import BaseContainer
import json 
import os

class DetectContainer(BaseContainer):

    def __init__(self, name):
        super().__init__('detect', name)

    def process(self, job_dir):
        self.extract("/tmp/die-out.json", job_dir)
        self.extract("/tmp/objdump-out.txt", job_dir)
        self.extract("/tmp/file-out.txt", job_dir)
        self.extract("/tmp/readelf-out.txt", job_dir)
        self.extract("/tmp/readpe-out.json", job_dir)
        self.extract("/tmp/hashes", job_dir)


        output = {
            "file_string": "",
            "arch": "UNKNOWN",
            "bits": "UNKNOWN",
            "format": "UNKNOWN",
            "type": "UNKNOWN",
            "hashes": {
                "sha256": "",
                "sha1": "",
                "md5": ""
            },
            "detects": []
        }

        file_output = open(os.path.join(job_dir, "file-out.txt"))
        file_data = file_output.read()
        file_output.close()

        output['file_string'] = file_data.split(":", 1)[1].strip()

        if "PE32" in output['file_string']:
            readpe_output = open(os.path.join(job_dir, "readpe-out.json"))
            readpe_data = json.load(readpe_output)
            readpe_output.close()

            machine = readpe_data["COFF/File header"]['Machine']
            machine_split = machine.split(" ", 1)
            if machine_split[1] == "IMAGE_FILE_MACHINE_AMD64":
                output['bits'] = "64"
                output['arch'] = 'amd64'
            elif machine_split[1] == "IMAGE_FILE_MACHINE_I386":
                output['bits'] = "32"
                output['arch'] = 'i386'
            output["format"] = "pe"

            characteristics = readpe_data["COFF/File header"]['Characteristics names']
            if "IMAGE_FILE_EXECUTABLE_IMAGE" in characteristics:
                if "IMAGE_FILE_DLL" in characteristics:
                    output['type'] = "library"
                else:
                    output['type'] = "executable"


            
        elif "ELF" in output['file_string']:
            readelf_output = open(os.path.join(job_dir, "readelf-out.txt"))
            readelf_data = readelf_output.read()
            readelf_output.close()

            readelf_lines = readelf_data.strip().split("\n")

            data = {}

            for line in readelf_lines:
                line_split = line.split(":", 1)
                key = line_split[0].strip().lower()
                value = line_split[1].strip().lower()
                data[key] = value

            if output["format"] == 'elf32':
                output['bits'] = "32"
                output["format"] = "elf"
            elif output["format"] == 'elf64':
                output['bits'] = "64"
                output["format"] = "elf"

            
            if 'exec' in data['type']:
                output['type'] == 'executable'
            elif 'dyn' in data['type']:
                output['type'] == 'library'

            if 'x86-64' in data['machine']:
                output['arch'] = 'amd64'
            elif 'intel 80386' in data['machine']:
                output['arch'] = 'i386'
            elif 'mips' in data['machine']:
                if data['class'] == 'elf32':
                    output['arch'] = 'mips32'
                elif data['class'] == 'elf64':
                    output['arch'] = 'mips64'
                elif 'little endian' in data['data'] and data['class'] == 'elf32':
                    output['arch'] = 'mipsel'
            elif 'arm' in data['machine']:
                 output['arch'] = 'arm32'
            elif 'aarch64' in data['machine']:
                 output['arch'] = 'aarch64'

                
            


 
        # Add detect-it-easy data
        die_output = open(os.path.join(job_dir, "die-out.json"))
        die_data = json.load(die_output)
        die_output.close()

        if "detects" in die_data:
            output['detects'] = die_data['detects']

        # Add hashes
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



        




