#!/usr/bin/env node

// patch hook for https://git.sakamoto.pl/laudompat/copykitku

module.exports = function patchHook(patchContent) {
    [
        [/(?:youtube-|yt-?)dl\.org/g, 'haruhi.download'],
        [/youtube_dl/g, 'haruhi_dl'],
        [/youtube-dl/g, 'haruhi-dl'],
        [/youtubedl/g, 'haruhidl'],
        [/YoutubeDL/g, 'HaruhiDL'],
        [/ytdl/g, 'hdl'],
        [/yt-dl/g, 'h-dl'],
        [/ydl/g, 'hdl'],

        // prevent from linking to non-existent repository
        [/github\.com\/(?:yt|h)dl-org\/haruhi-dl/g, 'github.com/ytdl-org/youtube-dl'],
        [/github\.com\/rg3\/haruhi-dl/g, 'github.com/ytdl-org/youtube-dl'],
        // prevent changing the smuggle URLs (for compatibility with ytdl)
        [/__haruhidl_smuggle/g, '__youtubedl_smuggle'],
    ].forEach(([regex, replacement]) => patchContent = patchContent.replace(regex, replacement));
    return patchContent;
}
