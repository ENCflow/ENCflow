# Using ENCflow on Windows (for Unix beginners)

> English mirror of docs/windows.md. The Japanese file is the master copy.

ENCflow runs in Linux-like environments. If you have only ever used
Windows, that is fine — we recommend the following route.

## 1. Try it first with zero installation (5 minutes)

A Colab notebook lets you build, run, and visualize ENCflow entirely
in your browser. No administrator rights, no setup.

**[→ Run ENCflow on Colab](https://colab.research.google.com/github/ENCflow/ENCflow/blob/main/docs/en/colab_quickstart.ipynb)**

The `git clone` and `make` written in the notebook cells are the very
same Unix commands you will use in WSL below. Running them once here
makes everything that follows look familiar.

## 2. To continue, use WSL (the standard Linux environment on Windows)

WSL is an official Microsoft feature that puts Ubuntu (Linux) inside
Windows. Installation is a single command in PowerShell (as
administrator):

```powershell
wsl --install
```

After a reboot, open Ubuntu from the Start menu, choose a user name
and password, and then follow the
[installation guide](install.md):

```bash
sudo apt update && sudo apt install -y gfortran make git
git clone https://github.com/ENCflow/ENCflow.git
cd ENCflow/src && make install
cd ../test/wave && ./Run.sh
```

If you get stuck, see Microsoft's
[WSL installation guide](https://learn.microsoft.com/en-us/windows/wsl/install).

## These are all the commands you need (cheat sheet)

Day-to-day use of ENCflow involves about ten Unix commands. No further
preparation is needed.

| Command | Meaning | Example |
|---|---|---|
| `cd place` | Move to a folder | `cd ENCflow/test/wave` |
| `cd ..` | Go one folder up | |
| `ls` | List files in the current folder | |
| `pwd` | Show where you are | |
| `make install` | Build (compile) | run in src/ |
| `./Run.sh` | Run a script | in each test/ case |
| `./encflow param.txt` | Run ENCflow directly | |
| `cat file` / `less file` | Show a text file (quit less with `q`) | `less result/Log.txt` |
| `cp from to` | Copy a file | `cp param.txt param2.txt` |
| `Tab` key | Complete a partially typed file name | essential technique |
| `↑` key | Recall the previous command | essential technique |

## Exchanging files with the Windows side

- Type `\\wsl$` in the address bar of Explorer and the files inside
  WSL appear **as ordinary folders**. Note that what you see first is
  the root of the whole Linux system; your own files are under
  `Ubuntu` → `home` → `your user name` (the name you chose when you
  first started WSL). If you followed the steps above, ENCflow is at
  `\\wsl$\Ubuntu\home\username\ENCflow`. You will visit this place
  often, so **pinning it to Quick access** is convenient.
  Edit parameter files with Notepad or VS Code, open the text/CSV
  results in Excel, and open the GeoTIFF outputs in GIS software
  directly.
- For serious use, [VS Code](https://code.visualstudio.com/) with the
  "WSL" extension is comfortable (editing, terminal, and file browsing
  in one window).

## 3. Where WSL is not available

On school PCs and other machines where WSL cannot be enabled, the
Colab route in step 1 still works in the browser alone. ENCflow is
expected to work in native Windows environments (MSYS2 etc.) as well,
but this has not been verified yet, so WSL is the recommended path.
