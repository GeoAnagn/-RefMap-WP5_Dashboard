# Download and install nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash

# in lieu of restarting the shell
\. "$HOME/.nvm/nvm.sh"

# Download and install Node.js:
nvm install 24

# Verify the Node.js version:
node -v # Should print "v24.13.0".

# Verify npm version:
npm -v # Should print "11.6.2".

# Install Project Packages
npm install 

# To run localhost
npm run dev

If you want to add specific IP then use the "-- --host={desired_ip}"
If you want to add specific Port then use the "-- --port={desired_port}"
Note that if you modify the base port then you also need to edit the appropriate backend/dockerfiles to listen to those ports
 