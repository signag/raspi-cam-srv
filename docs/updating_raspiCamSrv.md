# Updating raspiCamSrv

[![Up](img/goup.gif)](./index.md)

Before updating, make sure that

- [video recording](./Phototaking.md#video) is stopped
- there are no active [photoseries](./PhotoSeries.md)
- [triggered capture](./Trigger.md) (motion tracking) is stopped
- server will not [start with stored configuration](./SettingsConfiguration.md)

The [Settings/Update](./SettingsUpdate.md) dialog is the easiest way for updating. 

Alternatively, you can configure [Versatile Buttons](./ConsoleVButtons.md) with similar commands as described in the following, so that update and server restart can be initiated directly from the Web UI.  
(Note that commands issued through Versatile Buttons execute from the root directory in the virtual environment)

For update, proceed as follows:    
(If running a Docker container see [Update Procedure for Docker Container](./SetupDocker.md#update-procedure))

1. Within a SSH session go to the **raspiCamSrv** root directory    
```cd ~/prg/raspi-cam-srv```
2. If you have made local changes (e.g. logging), you may need to reset the workspace with   
```git reset --hard```
3. If you have created unversioned files, you may need to clean the workspace with   
```git clean -fd```
4. Use [git fetch](https://git-scm.com/docs/git-fetch) to update to the latest version     
(normally you need to fetch only the ```main``` branch)     
```git fetch origin main --depth=1```    
As a result, you will see a summary of changes with respect to the previously installed version.
5. Use [git reset](https://git-scm.com/docs/git-reset) to reset the current branch head to origin/main    
```git reset --hard origin/main```    
As a result, you will see the new HEAD version.
6. Restart the service, depending on [how the service was installed](./service_configuration.md)    
```sudo systemctl restart raspiCamSrv.service```    
or    
```systemctl --user restart raspiCamSrv.service```
7. Check that the service started correctly     
```sudo journalctl -e```    
or    
```journalctl --user -e```
8. If you used [start with stored configuration](./SettingsConfiguration.md) before updating, you may now try to activate this again.<br>In cases where configuration parameters were not modified with the update, this will usually work.<br>If not, you will need to prepare and store your preferred configuration again.

In case that the server did not start correctly or if you see an unexpected behavior in the UI, you may have forgotten to deactivate [start with stored configuration](./SettingsConfiguration.md)<br>In this case, you can do the following:

- ```cd ~/prg/raspi-cam-srv/raspiCamSrv/static/config```
- Check whether a file ```_loadConfigOnStart.txt``` exists in this folder.
- If it exists, remove it:<br>```rm _loadConfigOnStart.txt```
- Then repeat step 4, above
