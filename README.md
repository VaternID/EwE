
# EwE (WIP)

This program shows visual novels you currently play in your Discord Activity.

![Sakuranotoki](image/screenshot_sakuranotoki.png)

## Install

Download from [Releases](../../releases) (WIP) or from source directly. 

## Get started

- Open EwE and click **Add Game**.
- Search VNDB or choose **Unknown VN**.
- Select the game by its running window, `.exe`, or running process.
- Set its name, cover, and presence text.
- Keep Discord desktop running and enable activity sharing in **Activity
  Privacy**.
- Launch the game. EwE then will shows the visual novel you played on your Discord Activity.

## How it works
EwE matches the executable by process name and path and remember related game
processes. If multiple games run, EwE shows one based on their start times.

## Files and settings

EwE stores its files beside the program:

- `settings.json` = preferences, API keys, and tokens. 
- `vnlist.json` = your games, playtime, and cached data.
- `Cache\` = downloaded images.
- `Saved\` = covers and icons saved from the program.

More details: [Configuration Reference](docs/configuration.md) and
[Technical Reference](docs/technical-reference.md).


## Screenshots
![Irosekai](image/screenshot_irosekai.png)
<details>
<summary>Main Window 1 </summary>

![main1](image/library.png)
</details>


<details>
<summary>Main Window 2 </summary>

![main2](image/library2.png)
</details>


<details>

<summary>Preview</summary>

![preview](image/preview.png)
</details>

<details>
<summary>Custom</summary>

![custom](image/custom.png)
</details>


## Future Plan
- Being able to detect VNs in emulator
- More Customization 
- Improving the Library


## License

See [LICENSE](LICENSE).
