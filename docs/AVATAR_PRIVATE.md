# Keeping the masked character private

The character's clips and poses must not live in this public repo. They sit in a separate **private** repo; the video workflows fetch it at run time with a read-only token. Without the token the reel is still made, just without the character.

## One-time setup (about 5 minutes)

1. **Create the private repo.** github.com/new, name `avatar-assets`, visibility **Private**.
2. **Upload the files** (Add file -> Upload files, up to 25 MB each):
   - the clips into a folder `clips/`, named `type_angle_take.mp4` (for example `clips/explain_F_01.mp4`; the guide has the names),
   - the still poses into a folder `poses/` (`pose1.jpg` ... `pose4.jpg`).
   Shrink clips first: `ffmpeg -i in.mp4 -vf scale=720:1280 -r 30 -an -c:v libx264 -crf 26 -preset slow out.mp4`
3. **Create a read-only token.** GitHub -> Settings -> Developer settings -> Personal access tokens -> Fine-grained tokens -> Generate new token.
   Repository access: **Only select repositories** -> `avatar-assets`. Permissions: **Contents: Read-only**. Pick an expiry (a year) and note the date.
4. **Add it here.** This repo -> Settings -> Secrets and variables -> Actions -> New repository secret: name `AVATAR_REPO_TOKEN`, value = the token.
   If your private repo has another name, add a repository *variable* `AVATAR_REPO` = `owner/name`.

## How it is used
- `video-agent-fast.yml` and `video-agent.yml` check the private repo out into `video-agent/assets/avatar-private/` (git-ignored) before the reel is built.
- `agent/clips.py` reads `avatar-private/clips/*.mp4`; `agent/avatar.py` reads `avatar-private/poses/pose*.jpg`.
- Only the clips a reel actually uses are copied into the render folder, and nothing from the private repo is committed or uploaded anywhere except the finished reel.

## Notes
- Poses committed earlier are still in this repo's history. Once the private repo works, they can be deleted from the public tree (the history copy stays unless the repo is rewritten).
- When the token expires the workflow step is skipped and reels come out without the character: renew the token and update the secret.
