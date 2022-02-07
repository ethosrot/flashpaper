# flashpaper
flashpaper is a Flask server implementation of the [fmrl](https://github.com/makeworld-the-better-one/fmrl) protocol, currently supporting version 0.1.1 of the core+following APIs.

flashpaper also implements an avatar hosting and delivery serivice to compliment the fmrl spec.

## Install
Currently, flashpaper may be deployed as a standalone flask app or as a docker image. The app does not include HTTPS support out of the box, so you will likely want to deploy this app in conjunction with an SSL-capable reverse-proxy.

### Standalone
... coming soon ...

### Docker
Follow the following steps to start up a HTTP fmrl server on port 5000. PLEASE NOTE that you will need to proxy this behind an HTTPS-capable reverse proxy to be compliant.

```shell
git clone git@github.com:ethosrot/flashpaper.git
cd flashpaper
docker build -t flashpaper .
docker run -d --name flashpaper-server -p 5000:5000 -v avatars:/usr/src/app/avatars -v data:/usr/src/app/data flashpaper
```
The above assumes persistently storing avatars and the database in named volumes. Adjust -v mounts to match if you prefer to store your data elsewhere.

## User Management
There is currently no user management interface. Users may be added by running the following:

*Standalone:*
```shell
./utility.sh create-user <username> <password>
```

*Docker:*
```shell
docker exec -it flashpaper-server ./utility.sh create-user <username> <password>
```
## License

MIT.
