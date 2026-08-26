# Using ENCflow on Windows (for Unix beginners)

> English mirror of docs/windows.md. The Japanese file is the master copy.

ENCflow runs in Linux-like environments. If you have only ever used
Windows, that is fine — we recommend the following route.

## 1. Try it first with zero installation (5 minutes)

A Colab notebook lets you build, run, and visualize ENCflow entirely
in your browser. No administrator rights, no setup. Running it does
require a (free) **Google account** — if you do not have one and do
not wish to create one, skip step 1 and **start with WSL in step 2
just below** (skipping step 1 causes no problem for what follows).

**[→ Run ENCflow on Colab](https://colab.research.google.com/github/ENCflow/ENCflow/blob/main/docs/en/colab_quickstart.ipynb)**

The `git clone` and `make` written in the notebook cells are the very
same Unix commands you will use in WSL below. Running them once here
makes everything that follows look familiar.

## 2. To continue, use WSL (the standard Linux environment on Windows)

WSL is an official Microsoft feature that puts Ubuntu (Linux) inside
Windows. Installation is a single command in PowerShell opened **as
administrator**: search for "PowerShell" in the Start menu (or the
taskbar search box), then **right-click "Windows PowerShell" →
"Run as administrator"** (answer "Yes" when asked "Do you want to
allow this app to make changes to your device?"). In the blue window
that opens, type the following and press Enter:

```powershell
wsl --install    # install WSL and Ubuntu
```

After a reboot, open Ubuntu from the Start menu, choose a user name
and password, and then follow the
[installation guide](install.md):

```bash
sudo apt update && sudo apt install -y gfortran make git   # install the compiler etc.
git clone https://github.com/ENCflow/ENCflow.git           # fetch all of ENCflow
cd ENCflow/src && make install                             # move there and build
cd ../test/wave && ./Run.sh                                # run an example to verify
```

If you get stuck, see Microsoft's
[WSL installation guide](https://learn.microsoft.com/en-us/windows/wsl/install).

> **On a school or workplace network**: behind a proxy or content
> filter, `wsl --install` and `sudo apt update` may fail to download
> (timeouts or certificate errors). This is a restriction on the
> network side, not a mistake on your part — ask your network
> administrator. Even if it cannot be resolved right away, you can
> keep going with Colab alone, as described in
> "3. Where WSL is not available" at the end of this document.

### After installation — check where you are, then move

When the steps above finish, you are inside the directory (folder)
`ENCflow/test/wave`. In a terminal, what a command does depends on
"where you are", so first check your location with `pwd`:

```bash
pwd        # → shows /home/username/ENCflow/test/wave
```

The [tutorial](../../tutorials/wave/en/README.md) that comes next is
done in a different place, `ENCflow/tutorials/wave`. Moving around is
done with `cd` (`..` means "one directory up"):

```bash
cd ../../tutorials/wave
pwd        # → you are there if it shows .../ENCflow/tutorials/wave
```

Make it a habit to **confirm with `pwd` after every move** — it
avoids the single most common terminal stumble, "the command fails
because I am in the wrong place".

In WSL (Ubuntu), the **prompt** (the text shown to the left of where
you type) also always shows your current location:

```
username@machine:~/ENCflow/test/wave$
```

The part between `:` and `$` is where you are. The leading `~`
(tilde) means your **home directory** — the place you start in right
after logging in / opening WSL (its real path is `/home/username`).
Typing just `cd` takes you back to the home directory at any time.

The commands you will use are listed in the cheat sheet below.

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

The files inside WSL appear **as ordinary folders** in **Explorer** —
the standard Windows window for browsing files and folders (the
yellow folder icon on the taskbar, or `Windows key + E`). There are
two ways to get there:

- **From the left-hand pane**: scroll down the list on the left side
  of Explorer and you will find a **Linux** entry with a penguin icon
  (on recent Windows). From there, click through
  `Ubuntu` → `home` → `your user name` (the name you chose when you
  first started WSL).
- **From the address bar**: click the wide box at the top of Explorer
  that shows the current folder name (the address bar), type
  `\\wsl$`, and press Enter. What you see first is the root of the
  whole Linux system; your own files are likewise under
  `Ubuntu` → `home` → `your user name`.

If you followed the steps above, ENCflow is at
`\\wsl$\Ubuntu\home\username\ENCflow`. You will visit this place
often, so right-click the folder and **pin it to Quick access**.

## Viewing and editing files

Parameter files (`param_step1.txt` etc.) and the results and logs are
plain text files. There is no need to learn a terminal editor (vim
and the like) — open the directory in Explorer as in the previous
section and view/edit them **just like ordinary Windows files**.

- Text files (`.txt`) open in Notepad (or similar) with a double
  click. Other extensions (`.plt`, `.hdr`, ...) open via right-click
  → "Open with" → "Notepad".
- Edit in Notepad and **save — the WSL-side computation uses the file
  as-is** (Windows and WSL see the same actual file, so no copying or
  transferring is needed).
- Open the CSV results in Excel and the GeoTIFF outputs in GIS
  software (QGIS etc.) directly.
- When creating a new parameter file, rather than Notepad's "Save
  as", it is safer to **copy first in the terminal** — e.g.
  `cp param_step1.txt param2.txt` — and then open and edit the copy
  (this avoids accidents with the save location and file format).

For serious use, [VS Code](https://code.visualstudio.com/) with the
"WSL" extension is comfortable (editing, terminal, and file browsing
in one window).

## 3. Where WSL is not available

On school PCs and other machines where WSL cannot be enabled, or
where network restrictions block the installation, the Colab route in
step 1 still works in the browser alone. ENCflow is
expected to work in native Windows environments (MSYS2 etc.) as well,
but this has not been verified yet, so WSL is the recommended path.
