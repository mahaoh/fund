type JsonpCallback = (data: any) => void;

export const fetchFundGzJsonp = (code: string) =>
  new Promise<any>((resolve, reject) => {
    const callbackName = "jsonpgz";
    const previous = (window as any)[callbackName] as JsonpCallback | undefined;

    (window as any)[callbackName] = (data: any) => {
      if (previous) (window as any)[callbackName] = previous;
      else delete (window as any)[callbackName];
      resolve(data);
    };

    const script = document.createElement("script");
    script.src = `https://fundgz.1234567.com.cn/js/${code}.js?_=${Date.now()}`;
    script.async = true;
    script.onerror = () => {
      if (previous) (window as any)[callbackName] = previous;
      else delete (window as any)[callbackName];
      reject(new Error("fundgz jsonp failed"));
    };
    document.body.appendChild(script);
    script.onload = () => {
      setTimeout(() => {
        if (script.parentNode) script.parentNode.removeChild(script);
      }, 0);
    };
  });
