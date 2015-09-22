import psycopg2
import argparse
import sys
import requests
import os
import datetime
import re
# `from datetime import tzinfo, timedelta, datetime
from lxml import etree

parser = argparse.ArgumentParser(
    description='Create a target env.xml based off a source env.xml')
parser.add_argument("--src", help="Source Environment", required=True)
parser.add_argument("--dst", help="Target Environment", required=True)
parser.add_argument("--envdef", help="Path to the envdef's directory", required=True)
parser.add_argument("--description", help="Environments role", required=True)
parser.add_argument("--root", help="Alternate root path, usually only for search")
parser.add_argument("--tenant", help="look it up in the spreadsheet", required=True)
parser.add_argument("--udpip", help="Run the hafmaa tool", required=True)
parser.add_argument("--udpport", help="Run the hafmaa tool", required=True)
parser.add_argument("--jmsip", help="Run the hafmaa tool")
# parser.add_argument("--udp-jms-ip", help="Run the hafmaa tool", required=True)

args = parser.parse_args()

# Adding a slash to the path if it's not already there.
if args.envdef[-1] not in '/':
    args.envdef = args.envdef + '/'


class xmldata():
    def __init__(self, source, destination):
        '''
        Uses SVN_AUTH credentials located in your .bashrc
        '''
        # This section is for Remote URL access
        # url = (
        #     "http://svn.worksite.com/dcit-internal/siteops/tools/trunk/"
        #     "etc/envdef/envs/{0}/env.xml".format(environment)
        #     )
        # user, password = get_creds()
        # r = requests.get(url, auth=(user, password))
        # if r.status_code != 200:
        #     sys.exit(
        #         'There was an error retrieving the src environment tree from'
        #         ' svn.'
        #         )

        # Constructing the src file string
        src_file = args.envdef + 'envs/' + source + '/env.xml'
        f = open(src_file, 'r')
        p = etree.XMLParser(remove_blank_text=True)
        xml = etree.XML(f.read(), parser=p)
        f.close()

        # setting up some class variables/objects for easier access to xml sections
        self.xml = xml
        self.apps = xml.find('apps')
        self.env = xml.find('env')
        self.bare = xml.find('bare')
        self.sins = self.env.find('servers')
        self.ecnmap = self.env.find('ecnmap')
        self.dns = self.env.findall('dns')
        self.source = source
        self.destination = destination
        self.description = args.description
        # setting up the tenant
        if 'pci' in self.destination:
            self.tenant = args.tenant + '_pci'
        else:
            self.tenant = args.tenant

        # Running all the initial functions to setup our XML
        self.clean_sins()
        self.clean_dns()
        self.clean_ips()
        self.clean_bare_keys() # Need to split this out into separate things
        self.clean_env_details()
        self.clean_udpgroup()
        self.clean_envname()
        self.check_app_jms()
        self.create_file(xml)
        # print(etree.tostring(self.dns, pretty_print=True))

    def create_file(self, new_xml):
        '''
        function to dump our new_xml to a file
        '''
        destination_path = args.envdef + 'envs/' + self.destination + '/env.xml'
        if os.path.exists(destination_path):
            print(
                "\nThe --dst environment currently exists!\n\t{0}\nPlease rerun"
                " the command and specify a new dst.\n").format(destination_path)
            exit()
        else:
            os.makedirs(args.envdef + 'envs/' + self.destination)
        print("Trying to create the env.xml for: {0}".format(destination_path))
        f = open(destination_path, 'w')
        f.write(etree.tostring(new_xml,pretty_print=True))
        f.close

    def list_apps(self):
        for app in self.apps:
            if app.find('app-emerch-0'):
                print(etree.tostring(app, pretty_print=True))

    def check_app_jms(self):
        '''
        Check for the existence of appname, if found, and we didn't get a
        udp argument, exit. If we did get the UDP argument, set appropriately.
        '''
        for sin in self.sins:
            # check for the existence of appname 
            for app in sin:
                if app.text == 'appname' and args.jmsip == None:
                    print("This env has appname, you need to specify the --jmsip from the HAFMAA tool")
                    exit()


    def clean_sins(self):
        '''
        Takes a sin section and cleans out the hostnames and ip's
        '''
        # removing ip, host, and fqdn from sins if they exist
        for sin in self.sins:
            for key in ['ip', 'host', 'fqdn']:
                try:
                    sin.attrib.pop(key)
                except:
                    pass

    def clean_dns(self):
        '''
        removing dns entries from the env section
        '''
        for dns in self.dns:
            self.env.remove(dns)

    def clean_envname(self):
        '''
        Check for the existence of src envname in the apps and bare sections
        and replace it with dst envname.
        '''
        # Changing any bare keys to use ${env.name}
        for key in self.bare.findall('key'):
            key.attrib['value'] = key.attrib['value'].replace(self.source,'${env.name}')
        for app in self.apps:
            for key in app.findall('key'):
                if self.source in key.attrib['value']:
                    key.attrib['value'] = key.attrib['value'].replace(self.source,'${env.name}')

        # print(etree.tostring(key, pretty_print=True))

    def clean_ips(self):
        '''
        1. Check if the IP exists in the SINS section, if it does, make a
        reference to it
        '''
        # Sanitize URL's
        print("Removing IP's from BARE section")
        for ips in self.bare.findall('key'):
            # Check for IP's keys in BARE section and remove if found
            pass
            if re.findall(r'[0-9]+(?:\.[0-9]+){3}', ips.attrib['value']):
                # Find the original IP
                temp_ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', ips.attrib['value'])
                # Do the replace and store it in a string
                new_str = ips.attrib['value'].replace(temp_ip[0], '0.0.0.0')
                # Assign the new string back to the bare key value
                ips.attrib['value'] = new_str
                ips.set('FIXME', temp_ip[0])

        print("Removing IP's from APPS section")
        for app in self.apps:
            for ips in app.findall('key'):
                # Check for IP's keys in BARE section and remove if found
                if re.findall(r'[0-9]+(?:\.[0-9]+){3}', ips.attrib['value']):
                    # Find the original IP
                    temp_ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', ips.attrib['value'])
                    # Do the replace and store it in a string
                    new_str = ips.attrib['value'].replace(temp_ip[0], '0.0.0.0')
                    # Assign the new string back to the bare key value
                    ips.attrib['value'] = new_str
                    ips.set('FIXME', temp_ip[0])

        # print(etree.tostring(self.bare, pretty_print=True))

    def clean_udpgroup(self):
        '''
        set the udpgroup ip's from the arguments
        '''
        # Change the bare keys first.

        udpgroup_ip_key = self.bare.find('.//key[@name="partition.udpgroup.ip"]')
        udpgroup_port_key = self.bare.find('.//key[@name="partition.udpgroup.port"]')
        # Set the udpgroup IP
        try:
            udpgroup_ip_key.attrib['value'] = args.udpip
        except:
            # if we didn't find it, make a new one
            newkey = etree.SubElement(self.bare, 'key')
            newkey.set('name', 'partition.udpgroup.ip')
            newkey.set('value', args.udpip)

        # Set the udpgroup port
        try:
            udpgroup_port_key.attrib['value'] = args.udpport
        except:
            # if we didn't find it, make a new one
            newkey = etree.SubElement(self.bare, 'key')
            newkey.set('name', 'partition.udpgroup.port')
            newkey.set('value', args.udpport)
        # print(etree.tostring(self.bare, pretty_print=True))

    def clean_bare_keys(self):
        '''
        This is all our bare section work.
        '''
        # Iterate over all the bare keys. I'm not sure if this is required. I
        # do it because I'm looking for a wildcard. I think IN iterates also.
        bare_keys = self.bare.findall('key')
        for nfs in self.bare.findall('key'):
            # Check for nfs keys and remove if found
            if 'nfs.' in nfs.attrib['name']:
                self.bare.remove(nfs)

    def clean_env_details(self):
        '''
        set the headers in the env section
        '''
        self.env.attrib['name'] = self.destination
        self.env.attrib['description'] = self.description
        self.env.attrib['lease-start'] = str(datetime.date.today())
        self.env.attrib['lease-end'] = str(datetime.date.today() + datetime.timedelta(days=730))
        if args.root:
            self.env.attrib['root'] = args.root


def get_creds():
    '''
    Read an environment variable for SVN_AUTH and return the username and
    password
    '''
    svn_auth = os.environ.get('SVN_AUTH')
    if svn_auth:
        user, password = svn_auth.split(":")
        return user, password
    else:
        sys.exit(
            "We could not find the environment variable SVN_AUTH."
            "\n  Try adding the following to your ~/.bashrc ;"
            "\n  export SVN_AUTH=User:Sekretz"
            )


def check_pci():
    '''
    Check for the existence of a pci_version of the environment
    '''
    print("\nChecking for the existence of the -pci version")
    if os.path.exists(args.envdef + 'envs/' + args.src + '-pci'):
        print("\tFound " + args.envdef + 'envs/' + args.src + '-pci\n')
        return True
    else:
        print("\tNo PCI environment found, skipping!\n")


def main():
    # Check if the src environment has a PCI version
    if check_pci():
        my_pci_xml = xmldata(args.src + '-pci', args.dst + '-pci')

    # Check that the creation of our PCI env.xml was successful
    if os.path.exists(args.envdef + 'envs/' + args.dst + '-pci/env.xml'):
        print(
            "\nThe environment {0}-pci was created!\n".format(args.dst)
            )
    # Create our main xml
    my_xml = xmldata(args.src, args.dst)

    # Check that the destination environment was created
    if os.path.exists(args.envdef + 'envs/' + args.dst):
        print(
            "\nThe environment {0} was created!\n"
            "\nYou still have a few tasks to run:"
            "\n\t2. Check the ECNMAP"
            "\n\t3. svn add and svn commit the {0}".format(args.dst)
            )
    else:
        print("The self.create_file(xml) function had a accident. Did Mike comment it out again?")
main()



