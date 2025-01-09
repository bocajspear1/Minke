

def _has_api_call(thread_data, api_name, args=None, subcall=False):
    for api_call in thread_data:
        if api_name == api_call['api']:
            if args is None:
                return True
            elif isinstance(args, list):
                args_match = True
                print(args)
                print(api_call['args'])
                if len(args) == len(api_call['args']):
                    for i in range(len(api_call['args'])):
                        comp_item = api_call['args'][i]
                        check_item = args[i]
                        args_match = args_match and (comp_item == check_item)
                if args_match:
                    return True
        if subcall:
            subcall_found = _has_api_call(api_call['subcalls'], api_name, args=args, subcall=subcall)
            if subcall_found:
                return True
    return False

def any_thread_has_api_call(proc_data, api_name, args=None, subcall=False):
    for tid in proc_data['threads']:
        thread_data = proc_data['threads'][tid]
        found_thread = _has_api_call(thread_data, api_name, args=args, subcall=subcall)
        if found_thread:
            return True
    
    return False

def thread_has_api_call(thread_id, proc_data, api_name, args=None, subcall=False):
    for tid in proc_data['threads']:
        if int(tid) == int(thread_id):
            thread_data = proc_data['threads'][tid]
            found_thread = _has_api_call(thread_data, api_name, args=args, subcall=subcall)
            if found_thread:
                return True
            else:
                return False
    
    print("Not found")
    return False

def has_child_process(proc_data, child_name):
    for child in proc_data['child_processes']:
        proc_name = child['path'].split("\\")[-1]
        print(proc_name)
        if proc_name == child_name:
            return True
        has_child = has_child_process(child, child_name)
        if has_child:
            return True
    
    return False


def _is_in_order(syscall_list):
    counter = 0
    assert len(syscall_list) > 0
    for syscall in syscall_list:
        if syscall["counter"] > counter:
            counter = syscall["counter"]
            # print(counter)
            if len(syscall['subcalls']) > 0:
                sub_counter = _is_in_order(syscall['subcalls'])
                if sub_counter == 0:
                    return 0
                elif sub_counter <= counter:
                    print(sub_counter, counter)
                    return 0
                else:
                    # print(f"{counter} => {sub_counter}")
                    counter = sub_counter
                    
        else:
            print(syscall["counter"], counter)
            return 0
    return counter

def in_order(proc_data):
    for tid in proc_data['threads']:
        thread_data = proc_data['threads'][tid]
        if len(thread_data) > 0:
            counter = _is_in_order(thread_data)
            if counter == 0:
                print("Oh no")
                return False
    
    return True