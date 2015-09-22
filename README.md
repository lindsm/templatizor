### xmlcopy.py
`python xmlcopy.py --src parent_environment --dst child_environment --description "QA" --tenant np_dev --envdef /Users/lindsm/documents/Projects/envdef --udpip 10.1.4.3 --udpport 14010 --jmsip test`

This program will copy a specified environment, do a bit of sanitizing on it, and create a new env.xml in the appropriate directory as part of the repo. If a PCI version of --src exists, a --dst-pci env.xml will be created also. You have to know the path to your envdef's repo.  It does check for a specific app in the parent, and if found, will exit out if you DID NOT specify the IP.
