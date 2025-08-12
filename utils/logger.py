def log(new_line: bool = False, *args, **kwargs) -> None:
    print_output = ''
    for arg in args:
        print_output += '•\n %s' % (arg)
    for key, value in kwargs.items():
        print_output += "\n• %s: %s" % (key.capitalize().replace("_", " "), value)
    else:
        if new_line:
            print_output += '\n'
    print(print_output)