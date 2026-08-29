FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
# Run npm install at startup so new packages in package.json are always
# present even when the node_modules volume pre-dates the last image build.
CMD ["sh", "-c", "npm install --prefer-offline && npm run dev"]
